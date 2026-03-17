from __future__ import annotations

from re import Pattern, compile as re_compile

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.application.ports import (
    RuntimeSchemaFieldOrchestratorProtocol,
)
from src.modules.runtime_schema.domain.entities import FieldMetadata, ObjectMetadata
from src.modules.runtime_schema.domain.errors import DataSourceNotFoundError
from src.modules.runtime_schema.domain.repositories import DataSourceRepositoryProtocol
from src.modules.runtime_schema.infrastructure.migration_adapter import (
    SqlAlchemyRuntimeSchemaMigrationAdapter,
)

_IDENTIFIER_PATTERN: Pattern[str] = re_compile(r"^[a-z_][a-z0-9_]{0,62}$")


class SqlAlchemyRuntimeSchemaFieldOrchestrator(RuntimeSchemaFieldOrchestratorProtocol):
    def __init__(
        self,
        *,
        session: AsyncSession,
        data_source_repository: DataSourceRepositoryProtocol,
        migration_adapter: SqlAlchemyRuntimeSchemaMigrationAdapter,
    ):
        self._session = session
        self._data_source_repository = data_source_repository
        self._migration_adapter = migration_adapter

    async def on_field_created(
        self,
        *,
        object_metadata: ObjectMetadata,
        field_metadata: FieldMetadata,
    ) -> None:
        data_source = await self._data_source_repository.get_by_id(
            object_metadata.data_source_id
        )
        if data_source is None:
            raise DataSourceNotFoundError(object_metadata.data_source_id)

        table_name = _table_name_for_object(object_metadata)
        schema_name = data_source.schema

        await self._migration_adapter.add_column(
            schema_name=schema_name,
            table_name=table_name,
            column_name=field_metadata.name,
            field_type=field_metadata.type,
            is_nullable=field_metadata.is_nullable,
        )

        if field_metadata.default_value is not None:
            await self._backfill_default_value(
                schema_name=schema_name,
                table_name=table_name,
                column_name=field_metadata.name,
                default_value=field_metadata.default_value,
            )

        if field_metadata.is_unique:
            await self._migration_adapter.create_unique_index(
                schema_name=schema_name,
                table_name=table_name,
                column_name=field_metadata.name,
                index_name=_build_unique_index_name(
                    table_name=table_name,
                    column_name=field_metadata.name,
                ),
            )

    async def on_field_deleted(
        self,
        *,
        object_metadata: ObjectMetadata,
        field_metadata: FieldMetadata,
        hard_delete: bool,
    ) -> None:
        if not hard_delete:
            return

        data_source = await self._data_source_repository.get_by_id(
            object_metadata.data_source_id
        )
        if data_source is None:
            raise DataSourceNotFoundError(object_metadata.data_source_id)

        table_name = _table_name_for_object(object_metadata)
        schema_name = data_source.schema

        await self._migration_adapter.drop_index(
            schema_name=schema_name,
            index_name=_build_unique_index_name(
                table_name=table_name,
                column_name=field_metadata.name,
            ),
        )
        await self._migration_adapter.drop_column(
            schema_name=schema_name,
            table_name=table_name,
            column_name=field_metadata.name,
        )

    async def _backfill_default_value(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        default_value: object,
    ) -> None:
        table_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name=table_name,
        )
        quoted_column = _quoted_identifier(column_name)

        await self._session.execute(
            text(
                f"UPDATE {table_ref} "
                f"SET {quoted_column} = :default_value "
                f"WHERE {quoted_column} IS NULL"
            ),
            {"default_value": default_value},
        )


def _table_name_for_object(object_metadata: ObjectMetadata) -> str:
    if object_metadata.name_plural:
        candidate = object_metadata.name_plural
    else:
        candidate = f"{object_metadata.name_singular}s"

    normalized = candidate.strip().lower()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid runtime table name: '{candidate}'")
    return normalized


def _build_unique_index_name(*, table_name: str, column_name: str) -> str:
    normalized_table = table_name.strip().lower()
    normalized_column = column_name.strip().lower()
    index_name = f"uq_{normalized_table}_{normalized_column}"
    return index_name[:63]


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

    return f'{_quoted_schema_name(schema_name)}.{quoted_table}'


def _quoted_identifier(value: str) -> str:
    normalized = value.strip().lower()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(f"Invalid SQL identifier: '{value}'")
    return f'"{normalized}"'


def _quoted_schema_name(value: str) -> str:
    escaped = value.strip().replace('"', '""')
    return f'"{escaped}"'


__all__ = ["SqlAlchemyRuntimeSchemaFieldOrchestrator"]
