from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.infrastructure.contracts import DdlExecutorProtocol
from src.modules.runtime_schema.infrastructure.ddl_models import (
    DdlPlan,
    DdlOperation,
    ExecutionReport,
    MigrationJournalEntry,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO


class SqlAlchemyDdlExecutor(DdlExecutorProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def execute(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        plan: DdlPlan,
    ) -> ExecutionReport:
        del tenant_id, data_source_id, schema  # reserved for richer telemetry

        operations = list(plan.operations)
        journal_entries: list[MigrationJournalEntry] = []
        for operation in operations:
            try:
                async with self._session.begin_nested():
                    await self._session.execute(text(operation.sql))
            except Exception as exc:
                journal_entries.append(
                    MigrationJournalEntry.failed(
                        operation_key=operation.key,
                        operation_sql=operation.sql,
                        error_message=str(exc),
                    )
                )
                raise DdlExecutionError(
                    message=str(exc),
                    operations=tuple(operations),
                    journal_entries=tuple(journal_entries),
                ) from exc
            journal_entries.append(
                MigrationJournalEntry.applied(
                    operation_key=operation.key,
                    operation_sql=operation.sql,
                )
            )
        await self._session.flush()
        return ExecutionReport(
            operations=tuple(operations),
            journal_entries=tuple(journal_entries),
        )


class DdlExecutionError(RuntimeError):
    def __init__(
        self,
        *,
        message: str,
        operations: tuple[DdlOperation, ...],
        journal_entries: tuple[MigrationJournalEntry, ...],
    ):
        super().__init__(message)
        self.operations = operations
        self.journal_entries = journal_entries


__all__ = ["DdlExecutionError", "SqlAlchemyDdlExecutor"]
