from __future__ import annotations

import argparse
import sys
from uuid import UUID

from src.config import dnk_config
from src.modules.schema_registry.application.command import DiffSchemaCommand
from src.modules.schema_registry.domain.error import SchemaRegistryError
from src.modules.schema_registry.presentation.depends.management import (
    build_diff_schema_use_case,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.db.helper import db_helper
from src.modules.shared.db.uow import UnitOfWork
from src.modules.shared.infrastructure.time import UtcClock


async def handle_diff(args: argparse.Namespace) -> int:
    """Обрабатывает CLI-команду schema-registry diff и печатает summary результата."""
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = build_diff_schema_use_case(
                uow=uow,
                clock=UtcClock(),
            )
            result = await use_case.execute(
                DiffSchemaCommand(
                    tenant_id=EntityIdVO.from_value(args.tenant_id),
                    seed_path=args.seed_path,
                )
            )
    except SchemaRegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "OK "
        f"tenant_id={result.tenant_id} "
        f"schema_name={result.schema_name} "
        f"seed_path={result.seed_path} "
        f"operations={result.total_operations} "
        f"destructive={result.destructive_operations} "
        f"non_destructive={result.non_destructive_operations}"
    )
    return 0


async def handle_schema_registry_root(_args: argparse.Namespace) -> int:
    """Возвращает ошибочный exit code для запуска группы без подкоманды."""
    return 1


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Регистрирует argparse-команды schema-registry."""
    schema_registry_parser = subparsers.add_parser(
        "schema-registry",
        help="Schema registry management commands.",
    )
    schema_registry_subparsers = schema_registry_parser.add_subparsers(
        dest="schema_registry_command"
    )
    schema_registry_parser.set_defaults(handler=handle_schema_registry_root)

    diff_parser = schema_registry_subparsers.add_parser(
        "diff",
        help="Run schema diff for tenant runtime schema.",
    )
    diff_parser.add_argument(
        "tenant_id",
        type=UUID,
        help="Tenant identifier.",
    )
    diff_parser.add_argument(
        "--seed-path",
        default=dnk_config.DEFAULT_SEED_MODULE,
        help="Python module path that exposes SCHEMA_SEED.",
    )
    diff_parser.set_defaults(handler=handle_diff)


__all__ = [
    "handle_diff",
    "register",
]
