import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

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


def _serve(host: str, port: int) -> int:
    configuration = (
        os.environ.get("FR_LLM_BASE_URL"),
        os.environ.get("FR_LLM_MODEL"),
        os.environ.get("OPENAI_API_KEY"),
    )
    if any(not value for value in configuration):
        print("LLM configuration is incomplete", file=sys.stderr)
        return 2
    base_url, model, api_key = configuration
    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    llm = OpenAICompatibleLLM(
        base_url=base_url,
        model=model,
        api_key=api_key,
    )
    uvicorn.run(create_app(database_path, llm), host=host, port=port)
    return 0


def _test() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        shell=False,
        check=False,
    )
    return completed.returncode


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    if args.command == "init":
        return _init(_database_path(args.database))
    if args.command == "serve":
        return _serve(args.host, args.port)
    return _test()


if __name__ == "__main__":
    raise SystemExit(main())
