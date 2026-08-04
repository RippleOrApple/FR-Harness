import argparse
import getpass
import socket
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

import httpx
import uvicorn
from dotenv import load_dotenv
from pydantic import ValidationError

from fr_harness.app_paths import RuntimePaths
from fr_harness.config import load_config
from fr_harness.console import InteractiveConsole
from fr_harness.credentials import (
    CredentialStore,
    CredentialStoreError,
    resolve_api_key,
)
from fr_harness.db import Database
from fr_harness.demo import run_demo
from fr_harness.llm import OpenAICompatibleLLM
from fr_harness.memory import build_context
from fr_harness.task_service import TaskService
from fr_harness.web import create_app


VERSION = "1.0.2"

MANAGED_ENV_KEYS = {
    "FR_DATABASE_PATH",
    "FR_LLM_BASE_URL",
    "FR_LLM_MODEL",
}

PROVIDER_PRESETS = {
    "1": ("deepseek", "DeepSeek", "https://api.deepseek.com", "deepseek-v4-flash"),
    "2": ("openai", "OpenAI", "https://api.openai.com/v1", "gpt-4.1-mini"),
    "3": ("kimi", "Kimi / Moonshot", "https://api.moonshot.ai/v1", "kimi-k3"),
    "4": (
        "qwen",
        "Qwen / 阿里云百炼",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
    ),
    "5": (
        "siliconflow",
        "SiliconFlow",
        "https://api.siliconflow.cn/v1",
        "deepseek-ai/DeepSeek-V3",
    ),
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fr-harness",
        description="FR-Harness 安全编程 Agent",
    )
    parser.add_argument("--version", action="version", version=f"FR-Harness {VERSION}")
    subcommands = parser.add_subparsers(dest="command")

    subcommands.add_parser("run", help="启动交互式修复任务菜单")
    subcommands.add_parser("demo", help="运行无需网络和 API Key 的离线演示")

    init_parser = subcommands.add_parser("init", help="initialize the SQLite database")
    init_parser.add_argument("--database", type=Path)

    serve_parser = subcommands.add_parser("serve", help="start the WebUI")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    setup_parser = subcommands.add_parser(
        "setup", help="run an interactive first-run setup wizard"
    )
    setup_parser.add_argument("--host", default="127.0.0.1")
    setup_parser.add_argument("--port", type=int, default=8000)
    setup_parser.add_argument("--no-start", action="store_true")

    subcommands.add_parser("doctor", help="check local model configuration")

    credential_parser = subcommands.add_parser(
        "credential", help="manage the API credential in the system keyring"
    )
    credential_commands = credential_parser.add_subparsers(
        dest="credential_command", required=True
    )
    credential_commands.add_parser("set", help="store a new credential")
    credential_commands.add_parser("status", help="show credential configuration status")
    credential_commands.add_parser("update", help="replace the stored credential")
    credential_commands.add_parser("clear", help="remove the stored credential")

    subcommands.add_parser("test", help="run the project test suite")
    return parser


def _database_path(
    explicit: Path | None = None, *, default: Path | None = None
) -> Path:
    if explicit is not None:
        return explicit.expanduser()
    configured = os.environ.get("FR_DATABASE_PATH")
    if configured:
        return Path(configured).expanduser()
    return default or Path("fr_harness.sqlite3")


def _init(database_path: Path) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    Database(database_path).initialize()
    print(f"initialized database at {database_path}")
    return 0


def _hidden_input(prompt: str) -> str:
    return getpass.getpass(prompt)


def _prompt(prompt: str) -> str:
    return input(prompt)


def _stdin_is_interactive() -> bool:
    return sys.stdin.isatty()


def _load_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _redact_env_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("OPENAI_API_KEY="):
        return "OPENAI_API_KEY=<已隐藏>"
    return line


def _merge_env_values(path: Path, values: dict[str, str]) -> None:
    existing = _load_env_lines(path)
    seen: set[str] = set()
    output: list[str] = []
    for line in existing:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in values:
            output.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def _select_provider() -> tuple[str, str, str, str]:
    print("FR-Harness 初始配置向导\n")
    print("请选择模型供应商：")
    for key, (_, label, _, _) in PROVIDER_PRESETS.items():
        suffix = "（推荐）" if key == "1" else ""
        print(f"{key}. {label}{suffix}")
    print("6. 自定义 OpenAI 兼容接口")
    selected = _prompt("请选择模型供应商 [1]: ").strip() or "1"
    if selected == "6":
        return "custom", "自定义 OpenAI 兼容接口", "", ""
    try:
        return PROVIDER_PRESETS[selected]
    except KeyError:
        print("未知供应商选项。", file=sys.stderr)
        raise ValueError("unknown provider") from None


def _prompt_with_default(label: str, default: str) -> str:
    value = _prompt(f"{label} [{default}]: ").strip()
    return value or default


def _confirm(prompt: str, *, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = _prompt(f"{prompt} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def _is_valid_base_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) != 0


def _select_available_port(host: str, start: int) -> int | None:
    for port in range(start, start + 4):
        if _is_port_available(host, port):
            return port
        print(f"检测端口 {port}：已占用")
    return None


def _start_server_in_new_terminal(host: str, port: int) -> bool:
    command = (
        f"& .\\.venv\\Scripts\\python.exe -m fr_harness.cli serve --host {host} --port {port}"
    )
    if os.name == "nt":
        subprocess.Popen(
            ["powershell.exe", "-NoExit", "-Command", command],
            cwd=os.getcwd(),
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return True
    return False


def _safe_response_text(error: httpx.HTTPStatusError) -> str:
    text = error.response.text[:500]
    environment_key = os.environ.get("OPENAI_API_KEY")
    if environment_key:
        text = text.replace(environment_key, "[REDACTED]")
    return text


def _run_doctor(store: CredentialStore, env_path: Path = Path(".env")) -> int:
    load_dotenv(env_path, override=True)
    base_url = os.environ.get("FR_LLM_BASE_URL", "").strip()
    model = os.environ.get("FR_LLM_MODEL", "").strip()
    print("FR-Harness 配置自检")

    if not env_path.exists():
        print("[失败] 未找到 .env。请先运行 setup。")
        return 2
    print(".env：OK")

    if not base_url:
        print("[失败] FR_LLM_BASE_URL 未配置。")
        return 2
    if not _is_valid_base_url(base_url):
        print("[失败] FR_LLM_BASE_URL 缺少 http:// 或 https://")
        print(f"当前值：{base_url}")
        print("建议：使用类似 https://api.deepseek.com 的完整地址。")
        return 2
    print("Base URL：OK")

    if not model:
        print("[失败] FR_LLM_MODEL 未配置。")
        return 2
    print("模型名：OK")

    try:
        api_key, source = resolve_api_key(store)
    except (CredentialStoreError, ValueError) as error:
        print(f"[失败] 凭据读取失败：{error}")
        return 2
    if api_key is None:
        print("[失败] API Key 未配置。请运行 credential set 或 setup。")
        return 2
    print(f"API Key 来源：{source}")
    if source == "environment":
        print("提示：环境变量优先级高于 system keyring。")

    try:
        llm = OpenAICompatibleLLM(base_url=base_url, model=model, api_key=api_key)
        action = llm.next_action(
            build_context("Return a diagnostic Action JSON.", [], None)
        )
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        print(f"[失败] 模型服务返回 HTTP {status}。")
        if status == 401:
            print("建议：API Key 无效，请运行 credential update。")
        elif status == 402:
            print("建议：检查供应商账户余额。")
        elif status in {404, 422}:
            print("建议：检查 Base URL 和模型名是否匹配供应商。")
        elif status == 429:
            print("建议：稍后重试或降低请求频率。")
        print(f"响应摘要：{_safe_response_text(error)}")
        return 2
    except ValidationError:
        print("[失败] 模型没有返回合法 Action JSON。")
        print("建议：换用支持 JSON mode 的模型，或检查模型名。")
        return 2
    except Exception as error:
        print(f"[失败] 模型连接失败：{type(error).__name__}")
        print("建议：检查网络、Base URL、模型名和 API Key。")
        return 2

    print(f"HTTP 连接：OK")
    print(f"Action JSON：OK ({action.kind.value})")
    return 0


def _setup(
    host: str,
    port: int,
    no_start: bool,
    store: CredentialStore,
    runtime_paths: RuntimePaths | None = None,
) -> int:
    paths = runtime_paths or RuntimePaths.from_environment()
    paths.ensure()
    try:
        _, label, default_base_url, default_model = _select_provider()
    except ValueError:
        return 2
    if default_base_url:
        print(f"\n已选择：{label}")
        base_url = _prompt_with_default("Base URL", default_base_url)
        model = _prompt_with_default("模型名", default_model)
    else:
        base_url = _prompt("Base URL: ").strip()
        model = _prompt("模型名: ").strip()

    env_path = paths.env_file
    env_values = {
        "FR_LLM_BASE_URL": base_url,
        "FR_LLM_MODEL": model,
    }

    write_env = True
    if env_path.exists():
        print("\n检测到现有 .env：")
        for line in _load_env_lines(env_path):
            print(_redact_env_line(line))
        write_env = _confirm("是否覆盖模型配置？", default=False)
    if write_env:
        _merge_env_values(env_path, env_values)
        print(".env 已保存（未写入 API Key）。")
    else:
        print("保留现有 .env。")

    try:
        existing_key = store.get()
        if existing_key is None:
            value = _hidden_input("请输入 API Key（隐藏输入）: ")
            if not value:
                print("API Key 不能为空。配置已停止。", file=sys.stderr)
                return 2
            store.set(value)
            print("API Key 已保存到 system keyring。")
        elif _confirm("检测到 system keyring 中已有 API Key。是否更新？", default=False):
            value = _hidden_input("请输入新的 API Key（隐藏输入）: ")
            if not value:
                print("API Key 不能为空。配置已停止。", file=sys.stderr)
                return 2
            store.set(value)
            print("API Key 已更新到 system keyring。")
        else:
            print("沿用 system keyring 中已有 API Key。")
    except (CredentialStoreError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2

    database_path = _database_path(default=paths.database_file)
    _init(database_path)
    doctor_result = _run_doctor(store, env_path)
    if doctor_result != 0:
        print("自检失败，未启动 WebUI。")
        return doctor_result
    if no_start:
        print("配置完成。")
        print("启动交互模式：fr-harness run")
        return 0

    selected_port = _select_available_port(host, port)
    if selected_port is None:
        print(f"[失败] 端口 {port}-{port + 3} 都已被占用。")
        print(f"请手动运行：python -m fr_harness.cli serve --host {host} --port {port + 4}")
        return 2
    if _start_server_in_new_terminal(host, selected_port):
        print("WebUI 已在新的 PowerShell 窗口启动。")
        print(f"访问地址：http://{host}:{selected_port}/")
        print("如果要停止服务，请关闭新窗口或在新窗口按 Ctrl+C。")
        return 0

    print("自动打开新终端失败，请手动运行：")
    print(f"python -m fr_harness.cli serve --host {host} --port {selected_port}")
    return 2


def _credential(command: str, store: CredentialStore) -> int:
    try:
        if command == "status":
            _, source = resolve_api_key(store)
            if source == "not configured":
                print("credential is not configured")
            else:
                print(f"credential is configured ({source})")
            return 0

        if command == "set":
            if store.get() is not None:
                print(
                    "a system keyring credential already exists; use credential update",
                    file=sys.stderr,
                )
                return 2
            value = _hidden_input("API credential: ")
            if not value:
                print("credential cannot be empty", file=sys.stderr)
                return 2
            store.set(value)
            print("credential stored in system keyring")
            return 0

        if command == "update":
            if store.get() is None:
                print(
                    "no system keyring credential exists; use credential set",
                    file=sys.stderr,
                )
                return 2
            value = _hidden_input("New API credential: ")
            if not value:
                print("credential cannot be empty", file=sys.stderr)
                return 2
            store.set(value)
            print("credential updated in system keyring")
            return 0

        removed = store.clear()
        print(
            "credential cleared from system keyring"
            if removed
            else "system keyring credential was already absent"
        )
        return 0
    except (CredentialStoreError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


def _serve(
    host: str,
    port: int,
    store: CredentialStore,
    runtime_paths: RuntimePaths | None = None,
) -> int:
    paths = runtime_paths or RuntimePaths.from_environment()
    paths.ensure()
    base_url = os.environ.get("FR_LLM_BASE_URL")
    model = os.environ.get("FR_LLM_MODEL")
    if not base_url or not model:
        print("LLM configuration is incomplete", file=sys.stderr)
        return 2
    try:
        api_key, _ = resolve_api_key(store)
        if api_key is None:
            if not _stdin_is_interactive():
                print(
                    "API credential is not configured; run credential set first",
                    file=sys.stderr,
                )
                return 2
            api_key = _hidden_input("API credential: ")
            if not api_key:
                print("credential cannot be empty", file=sys.stderr)
                return 2
            store.set(api_key)
    except (CredentialStoreError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2

    database_path = _database_path(default=paths.database_file)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        configured_path = os.environ.get("FR_CONFIG_PATH")
        config = load_config(
            Path(configured_path).expanduser() if configured_path else paths.config_file
        )
    except FileNotFoundError:
        print("agent configuration file was not found", file=sys.stderr)
        return 2
    except (OSError, ValueError, ValidationError):
        print("agent configuration is invalid", file=sys.stderr)
        return 2
    llm = OpenAICompatibleLLM(
        base_url=base_url,
        model=model,
        api_key=api_key,
    )
    uvicorn.run(
        create_app(database_path, llm, config=config),
        host=host,
        port=port,
    )
    return 0


def _test() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        shell=False,
        check=False,
    )
    return completed.returncode


def _embedded_pytest() -> int:
    import pytest

    return pytest.main(["-q", "-p", "no:cacheprovider"])


def _configuration_is_complete(paths: RuntimePaths, store: CredentialStore) -> bool:
    load_dotenv(paths.env_file, override=True)
    if not os.environ.get("FR_LLM_BASE_URL") or not os.environ.get("FR_LLM_MODEL"):
        return False
    try:
        api_key, _ = resolve_api_key(store)
    except (CredentialStoreError, ValueError):
        return False
    return api_key is not None


def _build_task_service(paths: RuntimePaths, store: CredentialStore) -> TaskService:
    load_dotenv(paths.env_file, override=True)
    base_url = os.environ.get("FR_LLM_BASE_URL", "").strip()
    model = os.environ.get("FR_LLM_MODEL", "").strip()
    api_key, _ = resolve_api_key(store)
    if not base_url or not model or api_key is None:
        raise ValueError("模型配置不完整")
    database = Database(_database_path(default=paths.database_file))
    database.initialize()
    configured_path = os.environ.get("FR_CONFIG_PATH")
    config = load_config(
        Path(configured_path).expanduser() if configured_path else paths.config_file
    )
    llm = OpenAICompatibleLLM(base_url=base_url, model=model, api_key=api_key)
    return TaskService(database, llm, config=config)


def _interactive(paths: RuntimePaths, store: CredentialStore) -> int:
    paths.ensure()
    if not _configuration_is_complete(paths, store):
        print("首次使用需要先完成模型配置。")
        result = _setup("127.0.0.1", 8000, True, store, paths)
        if result != 0:
            return result

    try:
        service = _build_task_service(paths, store)
    except (CredentialStoreError, OSError, ValueError, ValidationError) as error:
        print(f"配置加载失败：{error}", file=sys.stderr)
        return 2

    console: InteractiveConsole

    def configure() -> None:
        nonlocal service
        result = _setup("127.0.0.1", 8000, True, store, paths)
        if result == 0:
            service = _build_task_service(paths, store)
            console.service = service

    console = InteractiveConsole(service, configure=configure)
    return console.run()


def main(
    argv: Sequence[str] | None = None,
    *,
    credential_store: CredentialStore | None = None,
    runtime_paths: RuntimePaths | None = None,
) -> int:
    selected_argv = list(argv) if argv is not None else sys.argv[1:]
    if selected_argv == ["_pytest"]:
        return _embedded_pytest()
    paths = runtime_paths or RuntimePaths.from_environment()
    paths.ensure()
    load_dotenv(paths.env_file)
    args = _parser().parse_args(selected_argv)
    store = credential_store or CredentialStore()
    if args.command in {None, "run"}:
        return _interactive(paths, store)
    if args.command == "demo":
        return run_demo()
    if args.command == "init":
        return _init(_database_path(args.database, default=paths.database_file))
    if args.command == "serve":
        return _serve(
            args.host,
            args.port,
            store,
            paths,
        )
    if args.command == "setup":
        return _setup(
            args.host,
            args.port,
            args.no_start,
            store,
            paths,
        )
    if args.command == "doctor":
        return _run_doctor(store, paths.env_file)
    if args.command == "credential":
        return _credential(
            args.credential_command,
            store,
        )
    return _test()


if __name__ == "__main__":
    raise SystemExit(main())
