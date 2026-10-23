"""Public migrations run against fresh, test-owned PostgreSQL databases only."""

import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.schema import BLANK_SCHEMA
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
                set(tables),
                {table.name for table in Base.metadata.tables.values()}
                | {"alembic_version_global"},
            )
            from alembic.autogenerate import compare_metadata
            from alembic.migration import MigrationContext

            # Сравниваем public с default schema без ложного различия FK public/None.
            metadata = MetaData()
            for table in Base.metadata.sorted_tables:
                table.to_metadata(
                    metadata,
                    schema=None,
                    referred_schema_fn=lambda table, schema, constraint, referred: (
                        BLANK_SCHEMA if referred == "public" else referred
                    ),
                )
            differences = await connection.run_sync(
                lambda conn: compare_metadata(
                    MigrationContext.configure(
                        conn,
                        opts={
                            "compare_type": True,
                            "compare_server_default": True,
                            "include_object": lambda obj, name, kind, reflected, compared: name
                            != "alembic_version_global",
                        },
                    ),
                    metadata,
                )
            )
            self.assertEqual(differences, [])
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

    async def test_current_revision_with_missing_table_is_not_ready(self):
        import src.app_factory as app_factory

        migrator = GlobalMigrator()
        async with self.engine.begin() as connection:
            await migrator.upgrade(connection)
        with patch.object(app_factory.db_helper, "engine", self.engine):
            transport = httpx.ASGITransport(app=app_factory.create_app())
            async with httpx.AsyncClient(
                transport=transport, base_url="http://localhost"
            ) as client:
                self.assertEqual((await client.get("/health/ready")).status_code, 200)
                async with self.engine.begin() as connection:
                    await connection.execute(text("DROP TABLE public.tenant_domains"))
                reply = await client.get("/health/ready")
                self.assertEqual(reply.status_code, 503)
                self.assertEqual(reply.json(), {"ready": False})
                self.assertEqual((await client.get("/health/live")).status_code, 200)
        async with self.engine.connect() as connection:
            self.assertEqual(await migrator.current(connection), (migrator.head(),))
            with self.assertRaisesRegex(GlobalSchemaNotReadyError, "tenant_domains"):
                await migrator.require_current(connection)
            self.assertIsNone(
                await connection.scalar(
                    text("SELECT to_regclass('public.tenant_domains')")
                )
            )

    async def test_resource_inspection_after_fresh_upgrade(self) -> None:
        """Начальная схема содержит реестр доменов для проверки ресурсов."""
        from src.modules.control_plane.infrastructure.tenancy_adapter import (
            TenancyAdapter,
        )

        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
        async with async_sessionmaker(self.engine)() as session:
            self.assertEqual(
                await TenancyAdapter(session, "dnk_").inspect(
                    uuid4(), "new.example.test", "new"
                ),
                "absent",
            )

    async def test_upgrade_preserves_existing_domain_records(self):
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
        tenant_id, domain_id = uuid4(), uuid4()
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO public.tenants (id, name, external_id) VALUES (:id, 'Existing', 'existing')"
                ),
                {"id": tenant_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO public.tenant_domains (id, tenant_id, service_type, kind, host, is_primary, is_wildcard) VALUES (:id, :tenant, 'console', 'default', 'existing.example.test', true, false)"
                ),
                {"id": domain_id, "tenant": tenant_id},
            )
            before = (
                await connection.execute(text("SELECT * FROM public.tenant_domains"))
            ).all()
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            await GlobalMigrator().require_current(connection)
            self.assertEqual(
                (
                    await connection.execute(
                        text("SELECT * FROM public.tenant_domains")
                    )
                ).all(),
                before,
            )
