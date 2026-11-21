from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

from src.modules.shared.infrastructure.persistence.alembic_lock import (
    serialized_alembic,
)

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory, Script
from alembic.script.base import Script
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection

MIGRATIONS_PATH = Path(__file__).resolve().parents[6] / "migrations" / "tenant"


class TenantMigrationError(Exception):
    """Техническая ошибка подготовки или применения tenant-миграций."""


class TenantSchemaMissingError(TenantMigrationError):
    """Миграция требует существующую tenant-схему."""


def validate_schema_name(schema_name: str) -> None:
    """Отклоняет системные схемы и небезопасные SQL-идентификаторы."""
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema_name) or (
        schema_name in {"public", "information_schema", "tenant"}
        or schema_name.startswith("pg_")
    ):
        raise TenantMigrationError("Invalid tenant schema name.")


async def lock_tenant_schema(connection: AsyncConnection, schema_name: str) -> None:
    """Блокирует изменения схемы до завершения внешней транзакции."""
    validate_schema_name(schema_name)
    if not connection.in_transaction():
        raise TenantMigrationError("Tenant migrations require an active transaction.")
    key = int.from_bytes(
        hashlib.sha256(f"dnk:tenant-migration:{schema_name}".encode()).digest()[:8],
        signed=True,
    )
    await connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


async def schema_exists(connection: AsyncConnection, schema_name: str) -> bool:
    """Проверяет схему без изменения search_path."""
    validate_schema_name(schema_name)
    return bool(
        await connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = :name)"),
            {"name": schema_name},
        )
    )


class TenantMigrator:
    """Запускает Alembic на соединении и транзакции вызывающего кода."""

    def __init__(self, script_location: Path = MIGRATIONS_PATH) -> None:
        """Выбирает граф миграций, сохраняя управление транзакцией за вызывающим кодом."""
        self._script_location = script_location

    def config(self, schema_name: str) -> Config:
        """Создаёт независимую конфигурацию одного запуска."""
        validate_schema_name(schema_name)
        config = Config()
        config.set_main_option("script_location", str(self._script_location))
        config.set_main_option("path_separator", "os")
        config.attributes["tenant_schema"] = schema_name
        return config

    def head(self) -> str | None:
        """Возвращает единственную актуальную ревизию из файлов."""
        config = Config()
        config.set_main_option("script_location", str(self._script_location))
        return ScriptDirectory.from_config(config).get_current_head()

    async def upgrade(self, connection: AsyncConnection, schema_name: str) -> None:
        """Применяет ревизии до head без commit."""
        await self._migrate(connection, schema_name, command.upgrade, "head")

    async def downgrade(
        self, connection: AsyncConnection, schema_name: str, revision: str
    ) -> None:
        """Откатывает ревизии до заданной версии во внешней транзакции."""
        await self._migrate(connection, schema_name, command.downgrade, revision)

    async def _migrate(
        self,
        connection: AsyncConnection,
        schema_name: str,
        action: Callable[[Config, str], None],
        revision: str,
    ) -> None:
        """Применяет весь путь атомарно внутри внешней транзакции через savepoint."""
        await lock_tenant_schema(connection, schema_name)
        await self.require_schema(connection, schema_name)
        config = self.config(schema_name)

        def run(sync_connection: Connection) -> None:
            """Запускает Alembic на том же соединении и в текущей транзакции."""
            config.attributes["connection"] = sync_connection
            action(config, revision)

        # DB lock берётся первым: ожидание чужого commit не удерживает proxy lock.
        async with serialized_alembic():
            async with connection.begin_nested():
                await connection.run_sync(run)

    async def require_schema(
        self, connection: AsyncConnection, schema_name: str
    ) -> None:
        """Не позволяет management-команде создать отсутствующую схему."""
        if not await schema_exists(connection, schema_name):
            raise TenantSchemaMissingError(
                f"Tenant schema '{schema_name}' does not exist."
            )

    async def current(
        self, connection: AsyncConnection, schema_name: str
    ) -> tuple[str, ...]:
        """Читает версию без создания таблицы версий и выполнения DDL."""
        await self.require_schema(connection, schema_name)

        def read_heads(sync_connection: Connection) -> tuple[str, ...]:
            """Читает текущие ревизии через синхронное представление соединения."""
            return MigrationContext.configure(
                sync_connection, opts={"version_table_schema": schema_name}
            ).get_current_heads()

        return await connection.run_sync(read_heads)

    async def revision(
        self, connection: AsyncConnection, schema_name: str, message: str
    ) -> Script | None | list[Script | None]:
        """Генерирует ревизию; connection должен принадлежать отдельному engine."""
        await lock_tenant_schema(connection, schema_name)
        await self.require_schema(connection, schema_name)
        config = self.config(schema_name)
        config.attributes["autogenerate"] = True

        def run(sync_connection: Connection) -> Script | None | list[Script | None]:
            """Генерирует файл ревизии из метаданных выделенного соединения."""
            config.attributes["connection"] = sync_connection
            return command.revision(config, message=message, autogenerate=True)

        async with serialized_alembic():
            return await connection.run_sync(run)
