from __future__ import annotations

from re import Pattern, compile as re_compile

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.domain.errors import InvalidFieldTypeError
from src.modules.runtime_schema.domain.value_objects import FieldType

_IDENTIFIER_PATTERN: Pattern[str] = re_compile(r"^[a-z_][a-z0-9_]{0,62}$")
_SCHEMA_PATTERN: Pattern[str] = re_compile(r"^[A-Za-z0-9_-]{1,128}$")


class SqlAlchemyRuntimeSchemaMigrationAdapter:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_column(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        field_type: FieldType | str,
        is_nullable: bool,
    ) -> None:
        sql_type = self.sql_type_for_field(field_type)
        table_ref = self._qualified_table(schema_name=schema_name, table_name=table_name)
        quoted_column = self._quoted_identifier(column_name)
        nullable_sql = "" if is_nullable else " NOT NULL"

        await self._session.execute(
            text(
                f"ALTER TABLE {table_ref} "
                f"ADD COLUMN {quoted_column} {sql_type}{nullable_sql}"
            )
        )

    async def drop_column(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
    ) -> None:
        table_ref = self._qualified_table(schema_name=schema_name, table_name=table_name)
        quoted_column = self._quoted_identifier(column_name)

        await self._session.execute(
            text(f"ALTER TABLE {table_ref} DROP COLUMN {quoted_column}")
        )

    async def create_unique_index(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        index_name: str,
    ) -> None:
        await self.create_index(
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            index_name=index_name,
            unique=True,
        )

    async def create_index(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        index_name: str,
        unique: bool,
    ) -> None:
        table_ref = self._qualified_table(schema_name=schema_name, table_name=table_name)
        quoted_column = self._quoted_identifier(column_name)
        quoted_index = self._quoted_identifier(index_name)
        unique_sql = "UNIQUE " if unique else ""

        await self._session.execute(
            text(
                f"CREATE {unique_sql}INDEX IF NOT EXISTS {quoted_index} "
                f"ON {table_ref} ({quoted_column})"
            )
        )

    async def drop_index(self, *, schema_name: str | None, index_name: str) -> None:
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        quoted_index = self._quoted_identifier(index_name)

        if schema_name and dialect_name == "postgresql":
            qualified_index = (
                f"{self._quoted_schema_name(schema_name)}.{quoted_index}"
            )
        else:
            qualified_index = quoted_index

        await self._session.execute(text(f"DROP INDEX IF EXISTS {qualified_index}"))

    async def drop_constraint(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        constraint_name: str,
    ) -> None:
        table_ref = self._qualified_table(schema_name=schema_name, table_name=table_name)
        quoted_constraint = self._quoted_identifier(constraint_name)

        await self._session.execute(
            text(
                f"ALTER TABLE {table_ref} "
                f"DROP CONSTRAINT IF EXISTS {quoted_constraint}"
            )
        )

    def sql_type_for_field(self, field_type: FieldType | str) -> str:
        parsed = self._parse_field_type(field_type)
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""

        if parsed == FieldType.PK:
            return "UUID" if dialect_name == "postgresql" else "CHAR(36)"
        if parsed == FieldType.STRING:
            return "VARCHAR(255)"
        if parsed == FieldType.LARGE_TEXT:
            return "TEXT"
        if parsed == FieldType.NUMBER:
            return "NUMERIC"
        if parsed == FieldType.BOOLEAN:
            return "BOOLEAN"
        if parsed == FieldType.DATE:
            return "DATE"
        if parsed == FieldType.DATETIME:
            return "TIMESTAMP WITH TIME ZONE"
        if parsed == FieldType.SELECT:
            return "VARCHAR(255)"
        if parsed == FieldType.MULTISELECT:
            return "JSONB" if dialect_name == "postgresql" else "JSON"

        raise InvalidFieldTypeError(str(field_type))

    @staticmethod
    def sql_type_for_dialect(field_type: FieldType | str, dialect_name: str) -> str:
        try:
            parsed = field_type if isinstance(field_type, FieldType) else FieldType(field_type)
        except ValueError as exc:
            raise InvalidFieldTypeError(str(field_type)) from exc

        if parsed == FieldType.PK:
            return "UUID" if dialect_name == "postgresql" else "CHAR(36)"
        if parsed == FieldType.STRING:
            return "VARCHAR(255)"
        if parsed == FieldType.LARGE_TEXT:
            return "TEXT"
        if parsed == FieldType.NUMBER:
            return "NUMERIC"
        if parsed == FieldType.BOOLEAN:
            return "BOOLEAN"
        if parsed == FieldType.DATE:
            return "DATE"
        if parsed == FieldType.DATETIME:
            return "TIMESTAMP WITH TIME ZONE"
        if parsed == FieldType.SELECT:
            return "VARCHAR(255)"
        if parsed == FieldType.MULTISELECT:
            return "JSONB" if dialect_name == "postgresql" else "JSON"

        raise InvalidFieldTypeError(str(field_type))

    def _qualified_table(self, *, schema_name: str | None, table_name: str) -> str:
        quoted_table = self._quoted_identifier(table_name)

        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        if not schema_name or dialect_name == "sqlite":
            return quoted_table

        return f"{self._quoted_schema_name(schema_name)}.{quoted_table}"

    @staticmethod
    def _quoted_identifier(value: str) -> str:
        normalized = value.strip()
        if not _IDENTIFIER_PATTERN.fullmatch(normalized):
            raise ValueError(f"Invalid SQL identifier: '{value}'")
        return f'"{normalized}"'

    @staticmethod
    def _quoted_schema_name(value: str) -> str:
        normalized = value.strip()
        if not _SCHEMA_PATTERN.fullmatch(normalized):
            raise ValueError(f"Invalid schema name: '{value}'")
        escaped = normalized.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _parse_field_type(field_type: FieldType | str) -> FieldType:
        try:
            return field_type if isinstance(field_type, FieldType) else FieldType(field_type)
        except ValueError as exc:
            raise InvalidFieldTypeError(str(field_type)) from exc


__all__ = ["SqlAlchemyRuntimeSchemaMigrationAdapter"]
