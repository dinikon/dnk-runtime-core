from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from uuid import UUID

from src.config import dnk_config
from src.modules.schema_registry.application.command import DiffSchemaCommand
from src.modules.schema_registry.application.dto import DiffSchemaResultDTO
from src.modules.schema_registry.domain.error import SchemaRegistryError
from src.modules.schema_registry.presentation.depends.management import (
    build_diff_schema_use_case,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.db.helper import db_helper
from src.modules.shared.db.uow import UnitOfWork
from src.modules.shared.infrastructure.time import UtcClock
from src.modules.tenancy.infrastructure.repository import SqlAlchemyTenantRepository


@dataclass(slots=True)
class _DiffAllSummary:
    """Агрегированная статистика schema-registry diff --all."""

    tenants: int = 0
    succeeded: int = 0
    failed: int = 0
    operations: int = 0
    destructive: int = 0
    non_destructive: int = 0

    def record_success(self, result: DiffSchemaResultDTO) -> None:
        """Добавляет результат успешно выполненного tenant diff."""
        self.succeeded += 1
        self.operations += result.total_operations
        self.destructive += result.destructive_operations
        self.non_destructive += result.non_destructive_operations


@dataclass(frozen=True, slots=True)
class _DiffFailure:
    """Ожидаемая ошибка diff для одного tenant."""

    tenant_id: UUID
    error: str


class _DiffAllRollback(Exception):
    """Sentinel exception that forces outer UoW rollback for diff --all."""

    def __init__(self, *, summary: _DiffAllSummary, failures: list[_DiffFailure]):
        super().__init__("schema-registry diff --all failed")
        self.summary = summary
        self.failures = failures


async def handle_diff(args: argparse.Namespace) -> int:
    """Обрабатывает CLI-команду schema-registry diff и печатает summary результата."""
    validation_error = _validate_diff_target(args)
    if validation_error is not None:
        print(validation_error, file=sys.stderr)
        return 1

    if getattr(args, "all_tenants", False):
        return await _handle_diff_all(args)

    return await _handle_diff_one(args)


async def _handle_diff_one(args: argparse.Namespace) -> int:
    """Выполняет schema diff для одного tenant."""
    tenant_id = args.tenant_id
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = build_diff_schema_use_case(
                uow=uow,
                clock=UtcClock(),
            )
            result = await _execute_diff(
                use_case=use_case,
                tenant_id=tenant_id,
                seed_path=args.seed_path,
            )
    except SchemaRegistryError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _print_diff_result(result)
    return 0


async def _handle_diff_all(args: argparse.Namespace) -> int:
    """Выполняет schema diff для всех tenants в одной общей транзакции."""
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            assert uow.session is not None
            tenant_repository = SqlAlchemyTenantRepository(uow.session)
            tenant_ids = await tenant_repository.list_ids()
            summary = _DiffAllSummary(tenants=len(tenant_ids))
            failures: list[_DiffFailure] = []
            use_case = build_diff_schema_use_case(
                uow=uow,
                clock=UtcClock(),
            )

            for tenant_id in tenant_ids:
                try:
                    async with uow.session.begin_nested():
                        result = await _execute_diff(
                            use_case=use_case,
                            tenant_id=tenant_id.uuid,
                            seed_path=args.seed_path,
                        )
                except SchemaRegistryError as exc:
                    summary.failed += 1
                    failure = _DiffFailure(
                        tenant_id=tenant_id.uuid,
                        error=str(exc),
                    )
                    failures.append(failure)
                    print(
                        f"ERROR tenant_id={failure.tenant_id} "
                        f"error={failure.error}",
                        file=sys.stderr,
                    )
                    continue

                summary.record_success(result)
                _print_diff_result(result)

            if failures:
                raise _DiffAllRollback(summary=summary, failures=failures)
    except _DiffAllRollback as exc:
        _print_diff_all_summary(exc.summary, rolled_back=True)
        return 2

    _print_diff_all_summary(summary, rolled_back=False)
    return 0


async def _execute_diff(
    *,
    use_case,
    tenant_id: UUID,
    seed_path: str,
) -> DiffSchemaResultDTO:
    """Запускает DiffSchemaUseCase для одного tenant."""
    return await use_case.execute(
        DiffSchemaCommand(
            tenant_id=EntityIdVO.from_value(tenant_id),
            seed_path=seed_path,
        )
    )


def _validate_diff_target(args: argparse.Namespace) -> str | None:
    """Проверяет, что указан ровно один target: tenant_id или --all."""
    tenant_id = getattr(args, "tenant_id", None)
    all_tenants = bool(getattr(args, "all_tenants", False))
    if tenant_id is not None and all_tenants:
        return "Provide either tenant_id or --all, not both."
    if tenant_id is None and not all_tenants:
        return "Provide tenant_id or --all."
    return None


def _print_diff_result(result: DiffSchemaResultDTO) -> None:
    """Печатает summary результата diff одного tenant."""
    print(
        "OK "
        f"tenant_id={result.tenant_id} "
        f"schema_name={result.schema_name} "
        f"seed_path={result.seed_path} "
        f"operations={result.total_operations} "
        f"destructive={result.destructive_operations} "
        f"non_destructive={result.non_destructive_operations}"
    )


def _print_diff_all_summary(summary: _DiffAllSummary, *, rolled_back: bool) -> None:
    """Печатает summary batch-запуска diff --all."""
    print(
        "SUMMARY "
        f"tenants={summary.tenants} "
        f"succeeded={summary.succeeded} "
        f"failed={summary.failed} "
        f"operations={summary.operations} "
        f"destructive={summary.destructive} "
        f"non_destructive={summary.non_destructive} "
        f"rolled_back={str(rolled_back).lower()}"
    )


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
        nargs="?",
        type=UUID,
        help="Tenant identifier.",
    )
    diff_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_tenants",
        help="Run schema diff for all tenants.",
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
