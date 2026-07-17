import argparse
import getpass
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from pydantic import ValidationError

from fr_harness.config import load_config
from fr_harness.credentials import (
    CredentialStore,
    CredentialStoreError,
    resolve_api_key,
)
from fr_harness.db import Database
from fr_harness.llm import OpenAICompatibleLLM
from fr_harness.web import create_app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fr-harness")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init_parser = subcommands.add_parser("init", help="initialize the SQLite database")
    init_parser.add_argument("--database", type=Path)

    serve_parser = subcommands.add_parser("serve", help="start the WebUI")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

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


def _database_path(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser()
    return Path(os.environ.get("FR_DATABASE_PATH", "fr_harness.sqlite3")).expanduser()


def _init(database_path: Path) -> int:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    Database(database_path).initialize()
    print(f"initialized database at {database_path}")
    return 0


def _hidden_input(prompt: str) -> str:
    return getpass.getpass(prompt)


def _stdin_is_interactive() -> bool:
    return sys.stdin.isatty()


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


def _serve(host: str, port: int, store: CredentialStore) -> int:
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

    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        config = load_config()
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


def main(
    argv: Sequence[str] | None = None,
    *,
    credential_store: CredentialStore | None = None,
) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    if args.command == "init":
        return _init(_database_path(args.database))
    if args.command == "serve":
        return _serve(
            args.host,
            args.port,
            credential_store or CredentialStore(),
        )
    if args.command == "credential":
        return _credential(
            args.credential_command,
            credential_store or CredentialStore(),
        )
    return _test()


if __name__ == "__main__":
    raise SystemExit(main())
