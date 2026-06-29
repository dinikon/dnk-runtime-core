from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.application.ports.tenant_schema_executor import (
    TenantSchemaExecutorPort,
)
from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    AddPrimaryKeyOperation,
    AlterColumnDefaultOperation,
    AlterColumnNullableOperation,
    AlterColumnTypeOperation,
    CreateIndexOperation,
    CreateSchemaOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
    DropPrimaryKeyOperation,
    DropTableOperation,
    MigrationOperation,
)
from src.modules.schema_registry.application.migration.plan import MigrationPlan
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaBackendError


class PostgresTenantSchemaExecutor(TenantSchemaExecutorPort):
    """PostgreSQL-адаптер, исполняющий migration plan tenant-схемы."""

    def __init__(
        self,
        session: AsyncSession,
        postgres_field_canonicalizer: PostgresFieldCanonicalizer,
    ) -> None:
        """Инициализирует executor SQLAlchemy-сессией и SQL-канонизатором типов."""
        self._session = session
        self._postgres_field_canonicalizer = postgres_field_canonicalizer

    async def execute(self, *, plan: MigrationPlan) -> None:
        """Выполняет операции плана последовательно и flush-ит сессию."""
        self._ensure_postgres()
        for operation in plan.operations:
            await self._execute_operation(operation)
        await self._session.flush()

    async def _execute_operation(self, operation: MigrationOperation) -> None:
        """Рендерит и выполняет DDL для одной поддержанной migration-операции."""
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
            column_type = self._postgres_field_canonicalizer.render_sql_preset(
                operation.sql_preset
            )
            sql = (
                "ALTER TABLE "
                f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                f"ADD COLUMN {self._qi(operation.column_name)} {column_type}"
            )
            if not operation.is_nullable:
                sql += " NOT NULL"
            if operation.default_value is not None:
                sql += f" DEFAULT {operation.default_value}"
            await self._session.execute(text(sql))
            return

        if isinstance(operation, DropColumnOperation):
            await self._session.execute(
                text(
                    "ALTER TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                    f"DROP COLUMN {self._qi(operation.column_name)}"
                )
            )
            return

        if isinstance(operation, AlterColumnDefaultOperation):
            sql = (
                "ALTER TABLE "
                f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                f"ALTER COLUMN {self._qi(operation.column_name)} "
            )
            if operation.default_value is None:
                sql += "DROP DEFAULT"
            else:
                sql += f"SET DEFAULT {operation.default_value}"
            await self._session.execute(text(sql))
            return

        if isinstance(operation, AlterColumnNullableOperation):
            sql = (
                "ALTER TABLE "
                f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                f"ALTER COLUMN {self._qi(operation.column_name)} "
            )
            if operation.is_nullable:
                sql += "DROP NOT NULL"
            else:
                sql += "SET NOT NULL"
            await self._session.execute(text(sql))
            return

        if isinstance(operation, AlterColumnTypeOperation):
            column_type = self._postgres_field_canonicalizer.render_sql_preset(
                operation.to_sql_preset
            )
            sql = (
                "ALTER TABLE "
                f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                f"ALTER COLUMN {self._qi(operation.column_name)} TYPE {column_type}"
            )
            if self._is_timestamp_utc_upgrade(operation):
                sql += (
                    f" USING {self._qi(operation.column_name)} "
                    "AT TIME ZONE 'UTC'"
                )
            await self._session.execute(text(sql))
            return

        if isinstance(operation, AddPrimaryKeyOperation):
            columns = ", ".join(self._qi(column) for column in operation.columns)
            await self._session.execute(
                text(
                    "ALTER TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                    f"ADD CONSTRAINT {self._qi(operation.constraint_name)} "
                    f"PRIMARY KEY ({columns})"
                )
            )
            return

        if isinstance(operation, DropPrimaryKeyOperation):
            await self._session.execute(
                text(
                    "ALTER TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                    f"DROP CONSTRAINT {self._qi(operation.constraint_name)}"
                )
            )
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

        if isinstance(operation, DropIndexOperation):
            await self._session.execute(
                text(
                    f"DROP INDEX {self._qualified_index(operation.schema_name, operation.index_name)}"
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

        if isinstance(operation, DropForeignKeyOperation):
            await self._session.execute(
                text(
                    "ALTER TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)} "
                    f"DROP CONSTRAINT {self._qi(operation.constraint_name)}"
                )
            )
            return

        if isinstance(operation, DropTableOperation):
            await self._session.execute(
                text(
                    "DROP TABLE "
                    f"{self._qualified_table(operation.schema_name, operation.table_name)}"
                )
            )
            return

        raise UnsupportedSchemaBackendError(
            f"Unsupported PostgreSQL migration operation '{type(operation).__name__}'."
        )

    def _ensure_postgres(self) -> None:
        """Проверяет, что текущий SQLAlchemy bind указывает на PostgreSQL dialect."""
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            raise UnsupportedSchemaBackendError(
                "schema_registry PostgreSQL adapters require a PostgreSQL backend."
            )

    @staticmethod
    def _qi(identifier: str) -> str:
        """Кавычит PostgreSQL-идентификатор для DDL."""
        return f'"{identifier}"'

    @classmethod
    def _qualified_table(cls, schema_name: str, table_name: str) -> str:
        """Возвращает fully-qualified имя таблицы schema.table."""
        return f"{cls._qi(schema_name)}.{cls._qi(table_name)}"

    @classmethod
    def _qualified_index(cls, schema_name: str, index_name: str) -> str:
        """Возвращает fully-qualified имя индекса schema.index."""
        return f"{cls._qi(schema_name)}.{cls._qi(index_name)}"

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        """Приводит on_delete к PostgreSQL DDL token с безопасным fallback."""
        mapping = {
            "restrict": "RESTRICT",
            "cascade": "CASCADE",
            "set null": "SET NULL",
            "set_null": "SET NULL",
            "no action": "NO ACTION",
            "no_action": "NO ACTION",
        }
        return mapping.get(value.strip().lower(), "RESTRICT")

    @staticmethod
    def _is_timestamp_utc_upgrade(operation: AlterColumnTypeOperation) -> bool:
        return (
            operation.from_sql_preset == SqlTypePresetEnum.TIMESTAMP
            and operation.to_sql_preset == SqlTypePresetEnum.TIMESTAMPTZ
        )
