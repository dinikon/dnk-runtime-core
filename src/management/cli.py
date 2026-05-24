import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path
import sys


def _bootstrap_pythonpath() -> None:
    """
    Keep compatibility with mixed imports in codebase:
    - src.*
    - modules.*
    """
    src_path = Path(__file__).resolve().parents[1]
    project_root = src_path.parent
    for raw_path in (project_root, src_path):
        path_str = str(raw_path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def build_parser() -> argparse.ArgumentParser:
    _bootstrap_pythonpath()
    from src.management.commands.communication import (
        register as register_communication,
    )
    from src.management.commands.events import (
        register as register_events,
    )
    from src.management.commands.jobs import (
        register as register_jobs,
    )
    from src.management.commands.schema_registry import (
        register as register_schema_registry,
    )

    parser = argparse.ArgumentParser(
        prog="dnk-manage",
        description="Management commands for dnk-runtime-core.",
    )
    subparsers = parser.add_subparsers(dest="commands")
    register_communication(subparsers)
    register_events(subparsers)
    register_jobs(subparsers)
    register_schema_registry(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        raise SystemExit(1)

    exit_code = asyncio.run(handler(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
