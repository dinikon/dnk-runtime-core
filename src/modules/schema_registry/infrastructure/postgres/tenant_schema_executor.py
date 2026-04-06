from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaBackendError
from src.modules.schema_registry.domain.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    CreateIndexOperation,
    CreateSchemaOperation,
    CreateTableOperation,
    MigrationOperation,
)
from src.modules.schema_registry.domain.migration.plan import MigrationPlan


class PostgresTenantSchemaExecutor(TenantSchemaExecutorPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def execute(self, *, plan: MigrationPlan) -> None:
        self._ensure_postgres()
        for operation in plan.operations:
            await self._execute_operation(operation)
        await self._session.flush()

    async def _execute_operation(self, operation: MigrationOperation) -> None:
        if isinstance(operation, CreateSchemaOperation):
            await self._session.execute(
                text(f"CREATE SCHEMA {self._qi(operation.schema_name)}")
            )
            return

        if isinstance(operation, CreateTableOperation):
            await self._session.execute(
                text(
                    "CREATE TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)} ()"
                )
            )
            return

        if isinstance(operation, AddColumnOperation):
            sql = (
                "ALTER TABLE "
                f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                f"ADD COLUMN {self._qi(operation.column_name)} {operation.column_type}"
            )
            if not operation.is_nullable:
                sql += " NOT NULL"
            if operation.default is not None:
                sql += f" DEFAULT {operation.default}"
            await self._session.execute(text(sql))
            return

        if isinstance(operation, CreateIndexOperation):
            unique = "UNIQUE " if operation.is_unique else ""
            columns = ", ".join(self._qi(column) for column in operation.columns)
            await self._session.execute(
                text(
                    f"CREATE {unique}INDEX {self._qi(operation.index_name)} "
                    f"ON {self._qualified_table(operation.schema_name, operation.table_name)} "
                    f"({columns})"
                )
            )
            return

        if isinstance(operation, AddForeignKeyOperation):
            on_delete = self._normalize_on_delete(operation.on_delete)
            await self._session.execute(
                text(
                    "ALTER TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                    f"ADD CONSTRAINT {self._qi(operation.constraint_name)} "
                    f"FOREIGN KEY ({self._qi(operation.column_name)}) "
                    f"REFERENCES {self._qualified_table(operation.target_schema_name, operation.target_table_name)} "
                    f"({self._qi(operation.target_column_name)}) "
                    f"ON DELETE {on_delete}"
                )
            )
            return

        raise UnsupportedSchemaBackendError(
            f"Unsupported PostgreSQL migration operation '{type(operation).__name__}'."
        )

    def _ensure_postgres(self) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            raise UnsupportedSchemaBackendError(
                "schema_registry PostgreSQL adapters require a PostgreSQL backend."
            )

    @staticmethod
    def _qi(identifier: str) -> str:
        return f'"{identifier}"'

    @classmethod
    def _qualified_table(cls, schema_name: str, table_name: str) -> str:
        return f"{cls._qi(schema_name)}.{cls._qi(table_name)}"

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        mapping = {
            "restrict": "RESTRICT",
            "cascade": "CASCADE",
            "set null": "SET NULL",
            "set_null": "SET NULL",
            "no action": "NO ACTION",
            "no_action": "NO ACTION",
        }
        return mapping.get(value.strip().lower(), "RESTRICT")
