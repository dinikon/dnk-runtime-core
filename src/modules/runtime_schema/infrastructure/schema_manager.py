from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.schema_manager import (
    TenantSchemaManagerProtocol,
)
from src.modules.runtime_schema.domain.entities import (
    SystemFieldDefinition,
    SystemObjectDefinition,
)
from src.modules.runtime_schema.domain.value_objects.field_type import (
    RuntimeSchemaFieldType,
)


class SqlAlchemyTenantSchemaManager(TenantSchemaManagerProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def ensure_system_object(
        self,
        *,
        schema: str,
        object_definition: SystemObjectDefinition,
    ) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            return

        qualified_table_name = self._quote_schema_table(
            schema, object_definition.table_name
        )
        create_columns_sql = ", ".join(
            self._build_create_column_sql(field_definition)
            for field_definition in object_definition.fields
        )
        await self._session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {qualified_table_name} "
                f"({create_columns_sql})"
            )
        )

        for field_definition in object_definition.fields:
            if field_definition.is_primary_key:
                continue
            await self._session.execute(
                text(
                    f"ALTER TABLE {qualified_table_name} "
                    f"ADD COLUMN IF NOT EXISTS "
                    f"{self._build_add_column_sql(field_definition)}"
                )
            )

    def _quote_schema_table(self, schema: str, table_name: str) -> str:
        bind = self._session.get_bind()
        quote = bind.dialect.identifier_preparer.quote
        return f"{quote(schema)}.{quote(table_name)}"

    def _build_create_column_sql(self, field_definition: SystemFieldDefinition) -> str:
        parts = [
            self._quote_identifier(field_definition.column_name),
            self._sql_type(field_definition.field_type),
        ]
        if field_definition.is_primary_key:
            parts.append("PRIMARY KEY")
        if not field_definition.is_nullable:
            parts.append("NOT NULL")
        default_sql = self._default_sql(field_definition)
        if default_sql is not None:
            parts.append(f"DEFAULT {default_sql}")
        if field_definition.is_unique and not field_definition.is_primary_key:
            parts.append("UNIQUE")
        return " ".join(parts)

    def _build_add_column_sql(self, field_definition: SystemFieldDefinition) -> str:
        parts = [
            self._quote_identifier(field_definition.column_name),
            self._sql_type(field_definition.field_type),
        ]
        if not field_definition.is_nullable:
            parts.append("NOT NULL")
        default_sql = self._default_sql(field_definition)
        if default_sql is not None:
            parts.append(f"DEFAULT {default_sql}")
        if field_definition.is_unique:
            parts.append("UNIQUE")
        return " ".join(parts)

    def _quote_identifier(self, value: str) -> str:
        bind = self._session.get_bind()
        return bind.dialect.identifier_preparer.quote(value)

    @staticmethod
    def _sql_type(field_type: RuntimeSchemaFieldType) -> str:
        mapping = {
            RuntimeSchemaFieldType.UUID: "UUID",
            RuntimeSchemaFieldType.STRING: "VARCHAR(255)",
            RuntimeSchemaFieldType.LONG_TEXT: "TEXT",
            RuntimeSchemaFieldType.DATETIME: "TIMESTAMP WITH TIME ZONE",
            RuntimeSchemaFieldType.BOOLEAN: "BOOLEAN",
            RuntimeSchemaFieldType.INTEGER: "BIGINT",
            RuntimeSchemaFieldType.DECIMAL: "NUMERIC(18, 2)",
            RuntimeSchemaFieldType.JSON: "JSONB",
        }
        return mapping[field_type]

    @staticmethod
    def _default_sql(field_definition: SystemFieldDefinition) -> str | None:
        if field_definition.default_sql is not None:
            return field_definition.default_sql
        if field_definition.default_value is None:
            return None
        if isinstance(field_definition.default_value, bool):
            return "TRUE" if field_definition.default_value else "FALSE"
        if isinstance(field_definition.default_value, (int, float)):
            return str(field_definition.default_value)
        if isinstance(field_definition.default_value, str):
            escaped = field_definition.default_value.replace("'", "''")
            return f"'{escaped}'"
        return None
