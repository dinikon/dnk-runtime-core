from __future__ import annotations

import json
from datetime import date, datetime
from re import Pattern, compile as re_compile
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_record.domain.errors import RuntimeRecordNotFoundError
from src.modules.runtime_record.domain.repositories import RuntimeValueRepositoryProtocol

_IDENTIFIER_PATTERN: Pattern[str] = re_compile(r"^[a-z_][a-z0-9_]{0,62}$")
_SCHEMA_PATTERN: Pattern[str] = re_compile(r"^[A-Za-z0-9_-]{1,128}$")


class SqlAlchemyRuntimeValueRepository(RuntimeValueRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def write_values(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        record_id: UUID,
        values: dict[str, object | None],
    ) -> None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name=table_name,
        )

        if not values:
            await self._assert_record_exists(table_ref=table_ref, record_id=record_id)
            return

        assignments: list[str] = []
        params: dict[str, object | None] = {"record_id": str(record_id)}

        for index, (column_name, value) in enumerate(values.items()):
            parameter_name = f"value_{index}"
            assignments.append(f"{_quoted_identifier(column_name)} = :{parameter_name}")
            params[parameter_name] = _serialize_runtime_value(value)

        result = await self._session.execute(
            text(
                f"UPDATE {table_ref} "
                f"SET {', '.join(assignments)} "
                f'WHERE "id" = :record_id'
            ),
            params,
        )
        if result.rowcount == 0:
            raise RuntimeRecordNotFoundError(table_name=table_name, record_id=record_id)

    async def read_values(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        record_id: UUID,
        field_names: tuple[str, ...],
    ) -> dict[str, object | None]:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name=table_name,
        )

        if not field_names:
            await self._assert_record_exists(table_ref=table_ref, record_id=record_id)
            return {}

        quoted_fields = ", ".join(_quoted_identifier(field_name) for field_name in field_names)
        rows = await self._session.execute(
            text(
                f"SELECT {quoted_fields} "
                f"FROM {table_ref} "
                f'WHERE "id" = :record_id'
            ),
            {"record_id": str(record_id)},
        )
        row = rows.first()
        if row is None:
            raise RuntimeRecordNotFoundError(table_name=table_name, record_id=record_id)

        return {
            field_names[index]: row[index]
            for index in range(len(field_names))
        }

    async def _assert_record_exists(self, *, table_ref: str, record_id: UUID) -> None:
        rows = await self._session.execute(
            text(f'SELECT 1 FROM {table_ref} WHERE "id" = :record_id'),
            {"record_id": str(record_id)},
        )
        if rows.first() is None:
            raise RuntimeRecordNotFoundError(table_name=table_ref, record_id=record_id)


def _serialize_runtime_value(value: object | None) -> object | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return json.dumps(list(value))
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def _qualified_table(
    *,
    session: AsyncSession,
    schema_name: str | None,
    table_name: str,
) -> str:
    quoted_table = _quoted_identifier(table_name)
    dialect_name = session.bind.dialect.name if session.bind else ""

    if not schema_name or dialect_name == "sqlite":
        return quoted_table

    return f"{_quoted_schema_name(schema_name)}.{quoted_table}"


def _quoted_identifier(value: str) -> str:
    normalized = value.strip().lower()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid SQL identifier: '{value}'")
    return f'"{normalized}"'


def _quoted_schema_name(value: str) -> str:
    normalized = value.strip()
    if not _SCHEMA_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid schema name: '{value}'")
    return f'"{normalized.replace("\"", "\"\"")}"'


__all__ = ["SqlAlchemyRuntimeValueRepository"]
