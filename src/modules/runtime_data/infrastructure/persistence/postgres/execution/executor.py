from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.domain.error import RuntimeDataPersistenceError
from src.modules.runtime_data.infrastructure.persistence.postgres.execution.statement_factory import (
    PostgresStatementFactory,
)
from src.modules.schema_registry.runtime import RuntimeFieldDescriptor


class PostgresSqlExecutor:
    """Executes PostgreSQL SQLAlchemy statements and maps persistence errors."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        statement_factory: PostgresStatementFactory | None = None,
        error_message: str,
    ) -> None:
        self._session = session
        self._statement_factory = statement_factory or PostgresStatementFactory()
        self._error_message = error_message

    async def execute(
        self,
        sql: str,
        params: Mapping[str, Any] | None = None,
        *,
        bind_fields: Mapping[str, RuntimeFieldDescriptor] | None = None,
    ):
        """Execute SQL and translate SQLAlchemy failures to runtime errors."""
        statement = self._statement_factory.statement(sql, bind_fields or {})
        try:
            if params is None:
                return await self._session.execute(statement)
            return await self._session.execute(statement, params)
        except SQLAlchemyError as exc:
            raise RuntimeDataPersistenceError(self._error_message) from exc


__all__ = ["PostgresSqlExecutor"]
