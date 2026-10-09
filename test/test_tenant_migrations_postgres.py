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
from uuid import UUID, uuid4

from alembic import command

from sqlalchemy import Column, MetaData, String, delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

import src.modules.persistence  # noqa: F401
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.management.cli import build_parser
from src.management.commands.tenant_migrations import handle
from src.modules.identity.application.user.command.create_tenant_admin.handler import (
    CreateTenantAdminHandler,
)
from src.modules.identity.infrastructure.persistence.models.user import UserModel
from src.modules.identity.infrastructure.user.persistence.repository import (
    SqlAlchemyUserRepository,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence import Base, UnitOfWork
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    MIGRATIONS_PATH,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrationError,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantSchemaMissingError,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    schema_exists,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant.command.create_tenant_command import (
    CreateTenantCommand,
)
from src.modules.tenancy.application.tenant.use_case.create_tenant import (
    CreateTenantUseCase,
)
from src.modules.tenancy.domain.service.tenant_onboarding import TenantOnboardingService
from src.modules.tenancy.domain.tenant.entity import Tenant
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
from src.modules.tenancy.infrastructure.repository.tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.modules.tenancy.infrastructure.repository.tenant_domain_repository import (
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
        self,
        connection: AsyncConnection,
        schema: str,
        *,
        warehouse_id: UUID | None = None,
        parent_id: UUID | None = None,
    ) -> UUID:
        """Заполняет историческую таблицу для проверки миграций без runtime-модели."""
        warehouse_id = warehouse_id or uuid4()
        await connection.execute(
            text(
                f'INSERT INTO "{schema}".warehouses '
                "(id, title, parent_id, created_by, updated_by) "
                "VALUES (:id, 'Warehouse', :parent, :actor, :actor)"
            ),
            {"id": warehouse_id, "parent": parent_id, "actor": uuid4()},
        )
        return warehouse_id

    async def test_inventory_removal_is_tenant_scoped_and_reversible(self) -> None:
        """Проверяет удаление Inventory, изоляцию tenant и восстановление пустой схемы."""
        schema = await self.new_schema(upgrade=False)
        other = await self.new_schema(upgrade=False)
        actor, sku_id, contact_id = uuid4(), uuid4(), uuid4()
        async with self.engine.begin() as connection:
            for tenant_schema in (schema, other):
                await self.migrator._migrate(
                    connection, tenant_schema, command.upgrade, "0015_remove_catalog"
                )
                await self.insert_warehouse(connection, tenant_schema)
                await connection.execute(
                    text(
                        f'INSERT INTO "{tenant_schema}".skus '
                        "(id, code, title, created_by, updated_by) "
                        "VALUES (:id, 'removed-sku', 'Removed SKU', :actor, :actor)"
                    ),
                    {"id": sku_id, "actor": actor},
                )
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=contact_id,
                    first_name="Preserved contact",
                    created_by=actor,
                    updated_by=actor,
                )
                .execution_options(schema_translate_map={"tenant": schema})
            )
            await connection.execute(
                text(f'CREATE TABLE "{schema}".legacy_objects (value text)')
            )
            await connection.execute(
                text(f"INSERT INTO \"{schema}\".legacy_objects VALUES ('preserved')")
            )
            tables_before = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
            )
            public_before = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema="public")
                )
            )
            await self.migrator.upgrade(connection, schema)
            await self.migrator.upgrade(connection, schema)
            tables_after = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
            )
            self.assertEqual(tables_after, tables_before - {"skus", "warehouses"})
            self.assertEqual(
                await connection.scalar(text(f'SELECT id FROM "{schema}".contacts')),
                contact_id,
            )
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT value FROM "{schema}".legacy_objects')
                ),
                "preserved",
            )
            self.assertEqual(
                await self.migrator.current(connection, other), ("0015_remove_catalog",)
            )
            self.assertEqual(
                await connection.scalar(text(f'SELECT id FROM "{other}".skus')),
                sku_id,
            )
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{other}".warehouses')
                ),
                1,
            )
            self.assertEqual(
                set(
                    await connection.run_sync(
                        lambda conn: inspect(conn).get_table_names(schema="public")
                    )
                ),
                public_before,
            )
            await self.migrator.downgrade(connection, schema, "0015_remove_catalog")
            restored = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
            )
            self.assertEqual(restored, tables_before)
            for table in ("skus", "warehouses"):
                self.assertEqual(
                    await connection.scalar(
                        text(f'SELECT count(*) FROM "{schema}"."{table}"')
                    ),
                    0,
                )
            root = await self.insert_warehouse(connection, schema)
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await self.insert_warehouse(
                        connection, schema, warehouse_id=uuid4(), parent_id=uuid4()
                    )
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            f'UPDATE "{schema}".warehouses SET parent_id=id WHERE id=:id'
                        ),
                        {"id": root},
                    )
            insert_sku = text(
                f'INSERT INTO "{schema}".skus '
                "(id, code, title, created_by, updated_by) "
                "VALUES (:id, 'unique-code', 'SKU', :actor, :actor)"
            )
            await connection.execute(insert_sku, {"id": uuid4(), "actor": actor})
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        insert_sku, {"id": uuid4(), "actor": actor}
                    )
            indexes = await connection.run_sync(
                lambda conn: inspect(conn).get_indexes("warehouses", schema=schema)
            )
            self.assertIn(
                "ix_warehouses_parent_id", {index["name"] for index in indexes}
            )
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await self.migrator.current(connection, schema), (self.migrator.head(),)
            )

    async def test_catalog_removal_preserves_other_modules_and_tenants(self) -> None:
        """Удаление Catalog ограничено tenant; downgrade возвращает только схему."""
        schema = await self.new_schema(upgrade=False)
        other = await self.new_schema(upgrade=False)
        async with self.engine.begin() as connection:
            for tenant_schema in (schema, other):
                await self.migrator.upgrade(connection, tenant_schema)
                await self.migrator.downgrade(
                    connection, tenant_schema, "0014_channel_publications"
                )
            warehouse_id = await self.insert_warehouse(connection, schema)
            tables_before = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
            )
            catalog_tables = {
                name for name in tables_before if name.startswith("catalog_")
            }
            self.assertEqual(len(catalog_tables), 14)
            actor, sku_id = uuid4(), uuid4()
            await connection.execute(
                text(
                    f'INSERT INTO "{schema}".skus '
                    "(id, code, title, created_by, updated_by) "
                    "VALUES (:id, 'kept-sku', 'Kept SKU', :actor, :actor)"
                ),
                {"id": sku_id, "actor": actor},
            )
            product_id = uuid4()
            await connection.execute(
                text(
                    f'INSERT INTO "{schema}".catalog_products '
                    "(id, kind, product_type_id, created_by, updated_by) "
                    f"SELECT :id, 'simple', id, :actor, :actor "
                    f"FROM \"{schema}\".catalog_product_types WHERE code = 'clean'"
                ),
                {"id": product_id, "actor": actor},
            )
            await connection.execute(
                text(
                    f'INSERT INTO "{schema}".catalog_variants (id, product_id, sku_id) '
                    "VALUES (:id, :product, :sku)"
                ),
                {"id": uuid4(), "product": product_id, "sku": sku_id},
            )
            await self.migrator._migrate(
                connection, schema, command.upgrade, "0015_remove_catalog"
            )
            tables_after = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
            )
            self.assertEqual(tables_after, tables_before - catalog_tables)
            self.assertEqual(
                await connection.scalar(text(f'SELECT id FROM "{schema}".skus')),
                sku_id,
            )
            self.assertEqual(
                await connection.scalar(text(f'SELECT id FROM "{schema}".warehouses')),
                warehouse_id,
            )
            self.assertTrue(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table(
                        "catalog_products", schema=other
                    )
                )
            )
            await self.migrator.downgrade(
                connection, schema, "0014_channel_publications"
            )
            restored = set(
                await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
            )
            self.assertEqual(restored, tables_before)
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{schema}".catalog_products')
                ),
                0,
            )
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{schema}".catalog_product_types')
                ),
                1,
            )
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await self.migrator.current(connection, schema),
                (self.migrator.head(),),
            )

    async def test_upgrade_repeat_downgrade_and_constraints(self) -> None:
        schema = await self.new_schema()
        async with self.engine.begin() as connection:
            original_path = await connection.scalar(text("SHOW search_path"))
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await connection.scalar(text("SHOW search_path")), original_path
            )
            self.assertEqual(
                await self.migrator.current(connection, schema),
                (self.migrator.head(),),
            )
            await self.migrator.downgrade(connection, schema, "0015_remove_catalog")
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
            self.assertFalse(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table("warehouses", schema=schema)
                )
            )

    async def test_price_list_archive_migration_upgrade_and_downgrade(self):
        schema = await self.new_schema()
        price_list_id = uuid4()
        actor_id = uuid4()
        async with self.engine.begin() as connection:
            columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("price_lists", schema=schema)
            )
            self.assertIn("archived_at", {column["name"] for column in columns})
            await connection.execute(
                text(
                    f'INSERT INTO "{schema}".price_lists '
                    "(id, title, created_by, updated_by, status, source_format, "
                    "source_url_secret, source_url_display) "
                    "VALUES (:id, 'Archive migration', :actor, :actor, "
                    "'archived', 'xml', 'encrypted', 'https://example.com/…')"
                ),
                {"id": price_list_id, "actor": actor_id},
            )
            await self.migrator.downgrade(
                connection, schema, "0004_partner_price_lists"
            )
            downgraded_columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("price_lists", schema=schema)
            )
            self.assertNotIn(
                "archived_at", {column["name"] for column in downgraded_columns}
            )
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT status FROM "{schema}".price_lists WHERE id = :id'),
                    {"id": price_list_id},
                ),
                "paused",
            )
            await self.migrator.upgrade(connection, schema)
            upgraded_columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("price_lists", schema=schema)
            )
            self.assertIn(
                "archived_at", {column["name"] for column in upgraded_columns}
            )

    async def test_crm_migration_constraints_indexes_and_round_trip(self):
        schema = await self.new_schema()
        other_schema = await self.new_schema()
        actor_id = uuid4()
        shared_contact_id = uuid4()
        async with self.engine.begin() as connection:
            for table_name in ("contacts", "companies"):
                self.assertTrue(
                    await connection.run_sync(
                        lambda conn, name=table_name: inspect(conn).has_table(
                            name, schema=schema
                        )
                    )
                )
            contact_indexes = await connection.run_sync(
                lambda conn: inspect(conn).get_indexes("contacts", schema=schema)
            )
            company_indexes = await connection.run_sync(
                lambda conn: inspect(conn).get_indexes("companies", schema=schema)
            )
            self.assertIn(
                "ix_contacts_name", {item["name"] for item in contact_indexes}
            )
            self.assertIn(
                "ix_companies_legal_name", {item["name"] for item in company_indexes}
            )
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=shared_contact_id,
                    first_name="Іван",
                    last_name=None,
                    middle_name=None,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                .execution_options(schema_translate_map={"tenant": schema})
            )
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=shared_contact_id,
                    first_name="Олена",
                    last_name=None,
                    middle_name=None,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                .execution_options(schema_translate_map={"tenant": other_schema})
            )
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(ContactModel.__table__)
                    .execution_options(schema_translate_map={"tenant": schema})
                ),
                1,
            )
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(ContactModel.__table__)
                    .execution_options(schema_translate_map={"tenant": other_schema})
                ),
                1,
            )
            await connection.execute(
                CompanyModel.__table__.insert()
                .values(
                    id=uuid4(),
                    legal_name="Acme",
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                .execution_options(schema_translate_map={"tenant": schema})
            )
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        ContactModel.__table__.insert()
                        .values(
                            id=uuid4(),
                            first_name="   ",
                            created_by=actor_id,
                            updated_by=actor_id,
                        )
                        .execution_options(schema_translate_map={"tenant": schema})
                    )
            await self.migrator.downgrade(
                connection, schema, "0009_crm_contact_companies"
            )
            self.assertEqual(
                await connection.scalar(text(f'SELECT name FROM "{schema}".companies')),
                "Acme",
            )
            await self.migrator.upgrade(connection, schema)
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT legal_name FROM "{schema}".companies')
                ),
                "Acme",
            )
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(f'UPDATE "{schema}".companies SET legal_name = :name'),
                        {"name": "   "},
                    )
            await self.migrator.downgrade(
                connection, schema, "0006_price_list_streaming"
            )
            for table_name in ("contacts", "companies"):
                self.assertFalse(
                    await connection.run_sync(
                        lambda conn, name=table_name: inspect(conn).has_table(
                            name, schema=schema
                        )
                    )
                )
            await self.migrator.upgrade(connection, schema)
            self.assertTrue(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table("contacts", schema=schema)
                )
            )

    async def test_price_list_streaming_upgrade_preserves_existing_quarantine(self):
        schema = await self.new_schema()
        price_id, actor_id, run_id = uuid4(), uuid4(), uuid4()
        async with self.engine.begin() as connection:
            await self.migrator.downgrade(
                connection, schema, "0005_price_list_management"
            )
            await connection.execute(
                text(
                    f"""INSERT INTO "{schema}".price_lists (id,title,created_by,updated_by,source_format,source_url_secret,source_url_display) VALUES (:id,'Existing',:actor,:actor,'xml','encrypted','masked')"""
                ),
                dict(id=price_id, actor=actor_id),
            )
            await connection.execute(
                text(
                    f"""INSERT INTO "{schema}".price_list_sync_runs (id,price_list_id,status,trigger,started_at,finished_at) VALUES (:id,:price,'partial','manual',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"""
                ),
                dict(id=run_id, price=price_id),
            )
            await connection.execute(
                text(
                    f"""INSERT INTO "{schema}".price_list_sync_items (sync_run_id,row_number,external_id) VALUES (:run,1,'quarantine')"""
                ),
                dict(run=run_id),
            )
            await self.migrator.upgrade(connection, schema)
            result = (
                await connection.execute(
                    text(
                        f'SELECT sync_run_id,external_id,quarantined FROM "{schema}".price_list_sync_items'
                    )
                )
            ).one()
            self.assertEqual(tuple(result), (run_id, "quarantine", True))
            indexes = await connection.run_sync(
                lambda conn: inspect(conn).get_indexes("partner_offers", schema=schema)
            )
            self.assertTrue(
                {"ix_partner_offers_list_id", "ix_partner_offers_search_document"}
                <= {item["name"] for item in indexes}
            )

    async def test_two_tenants_have_independent_versions_and_foreign_keys(self) -> None:
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
            for schema in (left, right):
                await self.migrator.downgrade(connection, schema, "0015_remove_catalog")
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
            await self.migrator.upgrade(connection, left)
            self.assertEqual(
                await self.migrator.current(connection, left), (self.migrator.head(),)
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
                    CreateTenantAdminHandler(
                        SqlAlchemyUserRepository(
                            uow.session, TenantSchemaNaming("dnk_")
                        )
                    )
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

    async def test_onboarding_commits_schema_admin_and_head(self) -> None:
        result = await self.onboard()
        schema = f"dnk_{result.tenant_id.hex}"
        async with self.engine.begin() as connection:
            self.assertEqual(
                await self.migrator.current(connection, schema),
                (self.migrator.head(),),
            )
            self.assertFalse(
                await connection.run_sync(
                    lambda conn: inspect(conn).has_table("warehouses", schema=schema)
                )
            )
            self.assertEqual(
                await connection.scalar(
                    select(UserModel.__table__.c.id)
                    .where(UserModel.__table__.c.id == result.user_id)
                    .execution_options(schema_translate_map={"tenant": schema})
                ),
                result.user_id,
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
                    (self.migrator.head(),),
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
                        "src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata.migration_metadata",
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

    async def test_autogenerate_detects_changes_and_owned_removals(self) -> None:
        schema = await self.new_schema()
        metadata = migration_metadata()
        metadata.tables["contacts"].append_column(
            Column("description", String(100), nullable=True)
        )
        with tempfile.TemporaryDirectory() as directory:
            generated = await self.generate_draft(schema, directory, metadata=metadata)
        self.assertIn("op.add_column('contacts'", generated)
        self.assertIn("description", generated)
        self.assertNotIn(schema, generated)
        with tempfile.TemporaryDirectory() as directory:
            removed = await self.generate_draft(schema, directory, metadata=MetaData())
        self.assertIn("op.drop_table('contacts')", removed)
        self.assertNotIn("description", ContactModel.__table__.c)

    async def test_autogenerate_base_preserves_foreign_keys_without_runtime_imports(
        self,
    ) -> None:
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
                self.assertIn("contacts.id", generated)
                self.assertNotIn("tenant.contacts", generated)
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
                    (self.migrator.head(),),
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
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import TenantMigrator
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
