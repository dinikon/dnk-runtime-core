"""Real PostgreSQL checks. TEST_POSTGRES_URL must point to a disposable test DB."""

import asyncio
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import Column, MetaData, String, delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

import src.modules.persistence  # noqa: F401
from src.management.cli import build_parser
from src.management.commands.tenant_migrations import handle
from src.modules.identity.application.user import UserService
from src.modules.identity.infrastructure.persistence.user import UserModel
from src.modules.identity.infrastructure.persistence.user_email import UserEmailModel
from src.modules.identity.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.inventory.infrastructure.persistence import WarehouseModel
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence import Base, UnitOfWork
from src.modules.shared.infrastructure.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    MIGRATIONS_PATH,
    TenantMigrator,
    TenantMigrationError,
    TenantSchemaMissingError,
    schema_exists,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant import (
    CreateTenantCommand,
    CreateTenantUseCase,
)
from src.modules.tenancy.domain.service import TenantOnboardingService
from src.modules.tenancy.domain.tenant import Tenant
from src.modules.tenancy.domain.tenant.schema_error import (
    TenantSchemaAlreadyExistsError,
)
from src.modules.tenancy.infrastructure.adapter.identity_provisioning import (
    IdentityProvisioningServiceAdapter,
)
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.persistence.tenant_domain import (
    TenantDomainModel,
)
from src.modules.tenancy.infrastructure.repository import (
    SqlAlchemyTenantRepository,
    SqlAlchemyTenantDomainRepository,
)
from src.modules.tenancy.presentation.depends.management import (
    TenantMigrationManagement,
)

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL 16 database."
)
class TenantMigrationPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.migrator = TenantMigrator()
        self.schemas = set()
        self.tag = uuid4().hex
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        try:
            async with self.engine.begin() as connection:
                ids = select(TenantModel.id).where(
                    TenantModel.external_id.like(f"{self.tag}%")
                )
                users = select(UserModel.id).where(UserModel.tenant_id.in_(ids))
                await connection.execute(
                    delete(UserEmailModel).where(UserEmailModel.user_id.in_(users))
                )
                await connection.execute(
                    delete(UserModel).where(UserModel.tenant_id.in_(ids))
                )
                await connection.execute(
                    delete(TenantDomainModel).where(
                        TenantDomainModel.tenant_id.in_(ids)
                    )
                )
                await connection.execute(
                    delete(TenantModel).where(TenantModel.id.in_(ids))
                )
                for schema in self.schemas:
                    await connection.execute(
                        DropSchema(schema, cascade=True, if_exists=True)
                    )
        finally:
            await self.engine.dispose()

    async def new_schema(self, *, upgrade=True):
        schema = f"dnk_test_{uuid4().hex}"
        self.schemas.add(schema)
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            if upgrade:
                await self.migrator.upgrade(connection, schema)
        return schema

    async def insert_warehouse(
        self, connection, schema, *, warehouse_id=None, parent_id=None
    ):
        warehouse_id = warehouse_id or uuid4()
        actor = uuid4()
        await connection.execute(
            WarehouseModel.__table__.insert()
            .values(
                id=warehouse_id,
                title="Warehouse",
                parent_id=parent_id,
                created_by=actor,
                updated_by=actor,
            )
            .execution_options(schema_translate_map={"tenant": schema})
        )
        return warehouse_id

    async def test_upgrade_repeat_downgrade_and_constraints(self):
        schema = await self.new_schema()
        async with self.engine.begin() as connection:
            original_path = await connection.scalar(text("SHOW search_path"))
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await connection.scalar(text("SHOW search_path")), original_path
            )
            self.assertEqual(
                await self.migrator.current(connection, schema), ("0001_warehouses",)
            )
            indexes = await connection.run_sync(
                lambda conn: inspect(conn).get_indexes("warehouses", schema=schema)
            )
            self.assertIn("ix_warehouses_parent_id", {item["name"] for item in indexes})
            checks = await connection.run_sync(
                lambda conn: inspect(conn).get_check_constraints(
                    "warehouses", schema=schema
                )
            )
            self.assertIn(
                "ck_warehouses_parent_not_self", {item["name"] for item in checks}
            )
            root = await self.insert_warehouse(connection, schema)
            child = await self.insert_warehouse(connection, schema, parent_id=root)
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(f'DELETE FROM "{schema}".warehouses WHERE id = :id'),
                        {"id": root},
                    )
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            f'UPDATE "{schema}".warehouses SET parent_id = id WHERE id = :id'
                        ),
                        {"id": child},
                    )
            await connection.execute(
                text(f'CREATE TABLE "{schema}".legacy_objects (id integer)')
            )
            await self.migrator.downgrade(connection, schema, "base")
            self.assertEqual(await self.migrator.current(connection, schema), ())
            self.assertTrue(await schema_exists(connection, schema))
            self.assertTrue(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table(
                        "legacy_objects", schema=schema
                    )
                )
            )
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{schema}".warehouses')
                ),
                0,
            )

    async def test_two_tenants_have_independent_versions_and_foreign_keys(self):
        left, right = await self.new_schema(), await self.new_schema(upgrade=False)
        async with self.engine.begin() as connection:
            self.assertEqual(await self.migrator.current(connection, right), ())
            self.assertFalse(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table(
                        "alembic_version", schema=right
                    )
                )
            )
            await self.migrator.upgrade(connection, right)
            root = await self.insert_warehouse(connection, left)
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await self.insert_warehouse(connection, right, parent_id=root)
            await self.insert_warehouse(connection, right, warehouse_id=root)
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{left}".warehouses')
                ),
                1,
            )
            await self.migrator.downgrade(connection, right, "base")
            self.assertEqual(
                await self.migrator.current(connection, left), ("0001_warehouses",)
            )

    async def onboard(self, *, fail=False, existing_schema=False):
        sessions = self.sessions
        schemas = self.schemas
        tag = self.tag

        class RecordingMigrator(TenantMigrator):
            async def upgrade(inner, connection, schema_name):
                await super().upgrade(connection, schema_name)
                if fail:
                    raise RuntimeError("Injected migration failure")

        class RecordingBootstrap(AlembicTenantSchemaBootstrapAdapter):
            async def bootstrap(inner, *, context):
                schemas.add(context.schema_name)
                if existing_schema:
                    await (await inner._session.connection()).execute(
                        CreateSchema(context.schema_name)
                    )
                await super().bootstrap(context=context)

        async with UnitOfWork(sessions) as uow:
            use_case = CreateTenantUseCase(
                tenant_onboarding_service=TenantOnboardingService(
                    SqlAlchemyTenantRepository(uow.session),
                    SqlAlchemyTenantDomainRepository(uow.session),
                ),
                identity_provisioning_service=IdentityProvisioningServiceAdapter(
                    UserService(SqlAlchemyUserRepository(uow.session))
                ),
                tenant_schema_bootstrap_context_factory=TenantSchemaBootstrapContextFactory(
                    schema_prefix="dnk_"
                ),
                tenant_schema_bootstrap_port=RecordingBootstrap(
                    uow.session, RecordingMigrator()
                ),
            )
            return await use_case.execute(
                CreateTenantCommand(
                    tenant_name=tag,
                    external_id=tag,
                    tenant_domain_host=f"{tag}.example.com",
                    user_first_name="Test",
                    user_last_name="Admin",
                    user_email=f"{tag}@example.com",
                )
            )

    async def test_onboarding_commits_schema_admin_and_head(self):
        result = await self.onboard()
        schema = f"dnk_{result.tenant_id.hex}"
        async with self.engine.begin() as connection:
            self.assertEqual(
                await self.migrator.current(connection, schema), ("0001_warehouses",)
            )
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{schema}".warehouses')
                ),
                0,
            )
            self.assertEqual(
                await connection.scalar(
                    select(UserModel.tenant_id).where(UserModel.id == result.user_id)
                ),
                result.tenant_id,
            )
            self.assertEqual(
                await connection.scalar(
                    select(TenantDomainModel.tenant_id).where(
                        TenantDomainModel.id == result.tenant_domain_id
                    )
                ),
                result.tenant_id,
            )

    async def test_migration_failure_rolls_back_entire_onboarding(self):
        with self.assertRaisesRegex(RuntimeError, "Injected"):
            await self.onboard(fail=True)
        async with self.engine.begin() as connection:
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(TenantModel)
                    .where(TenantModel.external_id == self.tag)
                ),
                0,
            )
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(UserEmailModel)
                    .where(UserEmailModel.email == f"{self.tag}@example.com")
                ),
                0,
            )
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(TenantDomainModel)
                    .where(TenantDomainModel.host == f"{self.tag}.example.com")
                ),
                0,
            )
            for schema in self.schemas:
                self.assertFalse(await schema_exists(connection, schema))

    async def test_existing_schema_conflict_rolls_back_onboarding(self):
        with self.assertRaises(TenantSchemaAlreadyExistsError):
            await self.onboard(existing_schema=True)
        async with self.engine.begin() as connection:
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(TenantModel)
                    .where(TenantModel.external_id == self.tag)
                ),
                0,
            )

    async def test_management_rejects_unknown_tenant_and_missing_schema(self):
        management = TenantMigrationManagement(
            self.sessions, self.engine.url, TenantSchemaNaming("dnk_"), self.migrator
        )
        with self.assertRaises(TenantMigrationError):
            await management.run_one(uuid4(), upgrade=True)
        tenant = Tenant.create(name=self.tag, external_id=self.tag)
        async with UnitOfWork(self.sessions) as uow:
            await SqlAlchemyTenantRepository(uow.session).add(tenant)
        with self.assertRaises(TenantSchemaMissingError):
            await management.run_one(tenant.id.uuid, upgrade=True)
        async with self.engine.begin() as connection:
            self.assertFalse(
                await schema_exists(connection, f"dnk_{tenant.id.uuid.hex}")
            )

    async def test_batch_commits_successful_tenants_around_a_failure(self):
        tenants = [
            Tenant.create(name=f"{self.tag}_{i}", external_id=f"{self.tag}_{i}")
            for i in range(3)
        ]
        tenants.sort(key=lambda tenant: str(tenant.id.uuid))
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyTenantRepository(uow.session)
            for tenant in tenants:
                await repository.add(tenant)
        for tenant in (tenants[0], tenants[2]):
            schema = f"dnk_{tenant.id.uuid.hex}"
            self.schemas.add(schema)
            async with self.engine.begin() as connection:
                await connection.execute(CreateSchema(schema))
        management = TenantMigrationManagement(
            self.sessions, self.engine.url, TenantSchemaNaming("dnk_"), self.migrator
        )
        args = build_parser().parse_args(["tenant-migrations", "upgrade", "--all"])
        with (
            patch(
                "src.management.commands.tenant_migrations.build_tenant_migration_management",
                return_value=management,
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(await handle(args), 2)
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                self.assertEqual(
                    await self.migrator.current(connection, schema),
                    ("0001_warehouses",),
                )
            self.assertFalse(
                await schema_exists(connection, f"dnk_{tenants[1].id.uuid.hex}")
            )

    async def generate_draft(self, schema, directory, *, metadata=None):
        location = Path(directory) / "tenant"
        shutil.copytree(MIGRATIONS_PATH, location)
        migrator = TenantMigrator(location)
        # This engine is intentionally separate: reflection temporarily sets its dialect default schema.
        engine = create_async_engine(TEST_URL, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                original_default = connection.dialect.default_schema_name
                if metadata is None:
                    script = await migrator.revision(connection, schema, "test draft")
                else:
                    with patch(
                        "src.modules.shared.infrastructure.persistence.tenant_migration_metadata.migration_metadata",
                        return_value=metadata,
                    ):
                        script = await migrator.revision(
                            connection, schema, "test draft"
                        )
                self.assertEqual(
                    connection.dialect.default_schema_name, original_default
                )
                return Path(script.path).read_text()
        finally:
            await engine.dispose()

    async def test_autogenerate_is_empty_at_head_and_ignores_legacy_tables(self):
        schema = await self.new_schema()
        async with self.engine.begin() as connection:
            await connection.execute(
                text(f'CREATE TABLE "{schema}".legacy_objects (id integer)')
            )
        with tempfile.TemporaryDirectory() as directory:
            generated = await self.generate_draft(schema, directory)
        self.assertNotIn("op.create_table", generated)
        self.assertNotIn("op.drop_", generated)
        self.assertNotIn("op.alter_", generated)
        self.assertNotIn("legacy_objects", generated)
        self.assertNotIn(schema, generated)

    async def test_autogenerate_detects_changes_and_owned_removals(self):
        schema = await self.new_schema()
        metadata = migration_metadata()
        metadata.tables["warehouses"].append_column(
            Column("description", String(100), nullable=True)
        )
        with tempfile.TemporaryDirectory() as directory:
            generated = await self.generate_draft(schema, directory, metadata=metadata)
        self.assertIn("op.add_column('warehouses'", generated)
        self.assertIn("description", generated)
        self.assertNotIn(schema, generated)
        with tempfile.TemporaryDirectory() as directory:
            removed = await self.generate_draft(schema, directory, metadata=MetaData())
        self.assertIn("op.drop_table('warehouses')", removed)
        self.assertNotIn("description", WarehouseModel.__table__.c)

    async def test_autogenerate_base_preserves_self_fk_without_runtime_imports(self):
        schema = await self.new_schema(upgrade=False)
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "tenant"
            shutil.copytree(MIGRATIONS_PATH, location)
            for revision in (location / "versions").glob("*.py"):
                revision.unlink()
            engine = create_async_engine(TEST_URL, poolclass=NullPool)
            try:
                async with engine.begin() as connection:
                    script = await TenantMigrator(location).revision(
                        connection, schema, "initial draft"
                    )
                    generated = Path(script.path).read_text()
                self.assertIn("warehouses.id", generated)
                self.assertNotIn("tenant.warehouses", generated)
                self.assertNotIn("StringUUID", generated)
                self.assertNotIn(schema, generated)
                async with engine.begin() as connection:
                    await TenantMigrator(location).upgrade(connection, schema)
            finally:
                await engine.dispose()

    async def test_parallel_migrations_same_and_different_schemas(self):
        first, second = await self.new_schema(upgrade=False), await self.new_schema(
            upgrade=False
        )

        async def upgrade(schema):
            async with self.engine.begin() as connection:
                await self.migrator.upgrade(connection, schema)
                self.assertEqual(
                    await self.migrator.current(connection, schema),
                    ("0001_warehouses",),
                )

        await asyncio.wait_for(
            asyncio.gather(
                upgrade(first), upgrade(first), upgrade(second), upgrade(second)
            ),
            timeout=20,
        )

    async def test_separate_processes_serialize_one_schema(self):
        schema = await self.new_schema(upgrade=False)
        code = """
import asyncio, os, sys
from sqlalchemy.ext.asyncio import create_async_engine
from src.modules.shared.infrastructure.persistence.tenant_migrations import TenantMigrator
async def main():
    engine = create_async_engine(os.environ['TEST_POSTGRES_URL'])
    try:
        async with engine.begin() as connection:
            await TenantMigrator().upgrade(connection, sys.argv[1])
    finally:
        await engine.dispose()
asyncio.run(main())
"""
        processes = [
            await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                code,
                schema,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            for _ in range(2)
        ]
        try:
            outputs = await asyncio.wait_for(
                asyncio.gather(*(p.communicate() for p in processes)), timeout=30
            )
            for process, (_, stderr) in zip(processes, outputs):
                self.assertEqual(process.returncode, 0, stderr.decode())
        finally:
            for process in processes:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
