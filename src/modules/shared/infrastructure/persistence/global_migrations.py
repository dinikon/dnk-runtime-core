"""Versioned public schema installation for new Runtime databases."""

import hashlib
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    serialized_alembic,
)

MIGRATIONS_PATH = Path(__file__).resolve().parents[5] / "migrations" / "global"
DEPLOYMENT_LOCK_KEY = int.from_bytes(
    hashlib.sha256(b"dnk:runtime:deployment").digest()[:8], signed=True
)


class GlobalSchemaNotReadyError(RuntimeError):
    """A migration must complete before this application can serve requests."""


class GlobalMigrator:
    def config(self) -> Config:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS_PATH))
        config.set_main_option("path_separator", "os")
        return config

    def head(self) -> str:
        return ScriptDirectory.from_config(self.config()).get_current_head()

    async def current(self, connection: AsyncConnection) -> tuple[str, ...]:
        return await connection.run_sync(
            lambda conn: MigrationContext.configure(
                conn,
                opts={
                    "version_table": "alembic_version_global",
                    "version_table_schema": "public",
                },
            ).get_current_heads()
        )

    async def require_current(self, connection: AsyncConnection) -> None:
        if await self.current(connection) != (self.head(),):
            raise GlobalSchemaNotReadyError(
                "Runtime public schema is not at the application revision; run database upgrade"
            )

    async def upgrade(self, connection: AsyncConnection) -> None:
        if not connection.in_transaction():
            raise RuntimeError("Public migrations require an active transaction")
        await connection.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": DEPLOYMENT_LOCK_KEY}
        )
        config = self.config()
        config.attributes["connection"] = None
        async with serialized_alembic():

            def run(conn):
                config.attributes["connection"] = conn
                command.upgrade(config, "head")

            await connection.run_sync(run)
