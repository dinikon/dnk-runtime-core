"""Public migrations run against fresh, test-owned PostgreSQL databases only."""

import os
import unittest
from uuid import uuid4

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
    GlobalSchemaNotReadyError,
)


class GlobalMigrationsPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        value = os.environ.get("DNK_TEST_DATABASE_URL")
        if not value:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is required for isolated PostgreSQL migration tests"
            )
        url = make_url(value).set(drivername="postgresql+asyncpg")
        self.name = "dnk_global_test_" + uuid4().hex
        self.admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with self.admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.name}"'))
        self.engine = create_async_engine(url.set(database=self.name))

    async def asyncTearDown(self):
        if hasattr(self, "engine"):
            await self.engine.dispose()
            async with self.admin.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{self.name}"'))
            await self.admin.dispose()

    async def test_fresh_upgrade_is_persistent_idempotent_and_covers_models(self):
        import src.modules.persistence  # noqa: F401
        from src.modules.shared.infrastructure.persistence.base import Base

        migrator = GlobalMigrator()
        async with self.engine.connect() as connection:
            with self.assertRaises(GlobalSchemaNotReadyError):
                await migrator.require_current(connection)
        async with self.engine.begin() as connection:
            await migrator.upgrade(connection)
        async with self.engine.begin() as connection:
            await migrator.upgrade(connection)
            await migrator.require_current(connection)
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema="public")
            )
            self.assertEqual(
                set(tables), set(Base.metadata.tables) | {"alembic_version_global"}
            )
            for table in Base.metadata.sorted_tables:
                columns = await connection.run_sync(
                    lambda conn: inspect(conn).get_columns(table.name, schema="public")
                )
                self.assertEqual(
                    {column["name"] for column in columns}, set(table.columns.keys())
                )

    async def test_existing_unversioned_database_is_not_adopted_or_reset(self):
        async with self.engine.begin() as connection:
            await connection.execute(
                text("CREATE TABLE tenants (id integer PRIMARY KEY)")
            )
            await connection.execute(text("INSERT INTO tenants VALUES (17)"))
        with self.assertRaises(Exception):
            async with self.engine.begin() as connection:
                await GlobalMigrator().upgrade(connection)
        async with self.engine.connect() as connection:
            self.assertEqual(
                await connection.scalar(text("SELECT id FROM tenants")), 17
            )
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema="public")
            )
            self.assertEqual(tables, ["tenants"])
