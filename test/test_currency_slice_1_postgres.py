"""Валютный срез в отдельных тестовых PostgreSQL DB и tenant-схемах."""

from collections.abc import AsyncGenerator
from decimal import Decimal
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock
from src.modules.tenancy.infrastructure.adapter.catalog_provisioning import (
    CatalogProvisioningAdapter,
)
from src.modules.catalog.application.product_type.facade import (
    CatalogProvisioningFacade,
)
from src.modules.catalog.infrastructure.product_type.persistence.repository import (
    SqlAlchemyProductTypeRepository,
)
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.presentation.persistence.depends import get_uow
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContextFactory,
)
from src.modules.tenancy.application.tenant.command.create_tenant.command import (
    CreateTenantCommand,
)
from src.modules.tenancy.application.tenant.command.create_tenant.handler import (
    CreateTenantHandler,
)
from src.modules.tenancy.application.tenant.onboarding import TenantOnboardingService
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.adapter.schema_bootstrap import (
    AlembicTenantSchemaBootstrapAdapter,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.adapter.currency_validator import (
    ReferenceDataCurrencyValidator,
)
from src.modules.tenancy.infrastructure.adapter.tenant_currency_settings import (
    TenantCurrencySettingsPersistenceAdapter,
)
from src.modules.tenancy.infrastructure.repository.tenant_domain_repository import (
    SqlAlchemyTenantDomainRepository,
)
from src.modules.tenancy.infrastructure.repository.tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.repository import (
    SqlAlchemyTenantCurrencySettingsRepository,
)
from src.modules.tenancy.infrastructure.tenant_currency_settings.persistence.query_repository import (
    SqlAlchemyTenantCurrencySettingsQueryRepository,
)
from src.modules.tenancy.presentation.http.router import router

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations/tenant/versions/0022_tenant_currency_settings.py"
)


async def apply_currency_migration(
    connection: AsyncConnection, schema: str, *, downgrade: bool = False
) -> None:
    """Применяет настоящую ревизию в тестовой схеме без зависимости от чужих моделей."""
    spec = importlib.util.spec_from_file_location(
        "currency_settings_migration", MIGRATION_PATH
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    await connection.execute(
        text("SELECT set_config('search_path', :schema, true)"), {"schema": schema}
    )

    def run(sync_connection) -> None:
        with Operations.context(MigrationContext.configure(sync_connection)):
            (migration.downgrade if downgrade else migration.upgrade)()

    await connection.run_sync(run)
    await connection.execute(text("SELECT set_config('search_path', 'public', true)"))


class CurrencySliceOnePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        value = os.environ.get("DNK_TEST_DATABASE_URL")
        if not value:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is required for isolated PostgreSQL tests"
            )
        url = make_url(value).set(drivername="postgresql+asyncpg")
        self.name = "dnk_currency_test_" + uuid4().hex
        self.admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with self.admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.name}"'))
        self.engine = create_async_engine(url.set(database=self.name))
        self.addAsyncCleanup(self.drop_database)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming("dnk_")
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            await connection.execute(
                text(
                    "INSERT INTO public.ref_currencies (code, numeric_code, name, minor_units, active) "
                    "VALUES ('UAH', '980', 'Hryvnia', 2, true), ('USD', '840', 'Dollar', 2, true), "
                    "('JPY', '392', 'Yen', 0, false)"
                )
            )

    async def drop_database(self) -> None:
        await self.engine.dispose()
        async with self.admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{self.name}"'))
        await self.admin.dispose()

    async def test_migration_defaults_are_tenant_local_and_preserve_existing_data(
        self,
    ) -> None:
        schemas = ["dnk_" + uuid4().hex for _ in range(2)]
        async with self.engine.begin() as connection:
            for schema in schemas:
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await connection.execute(
                    text(f'CREATE TABLE "{schema}".existing_data (id integer)')
                )
                await connection.execute(
                    text(f'INSERT INTO "{schema}".existing_data VALUES (17)')
                )
                await apply_currency_migration(connection, schema)
                self.assertEqual(
                    await connection.scalar(
                        text(
                            f'SELECT base_currency FROM "{schema}".tenant_currency_settings'
                        )
                    ),
                    "UAH",
                )
                self.assertEqual(
                    await connection.scalar(
                        text(f'SELECT id FROM "{schema}".existing_data')
                    ),
                    17,
                )
                columns = await connection.run_sync(
                    lambda conn: inspect(conn).get_columns(
                        "tenant_currency_settings", schema=schema
                    )
                )
                column = next(
                    item for item in columns if item["name"] == "base_currency"
                )
                self.assertFalse(column["nullable"])
                self.assertEqual(column["type"].length, 3)
            self.assertIsNone(
                await connection.scalar(
                    text("SELECT to_regclass('public.tenant_currency_settings')")
                )
            )
            columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns("tenants", schema="public")
            )
            self.assertNotIn("base_currency", {item["name"] for item in columns})
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(
                        f'UPDATE "{schemas[0]}".tenant_currency_settings SET base_currency = NULL'
                    )
                )
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await connection.execute(
                    text(f'UPDATE "{schemas[0]}".tenant_currency_settings SET id = 2')
                )
        async with self.engine.begin() as connection:
            await apply_currency_migration(connection, schemas[0], downgrade=True)
            self.assertIsNone(
                await connection.scalar(
                    text(f"SELECT to_regclass('{schemas[0]}.tenant_currency_settings')")
                )
            )
            self.assertIsNotNone(
                await connection.scalar(
                    text(f"SELECT to_regclass('{schemas[1]}.tenant_currency_settings')")
                )
            )

    async def test_validation_uses_only_active_catalog_currency(self) -> None:
        async with UnitOfWork(self.sessions) as uow:
            handler = ValidateCurrencyHandler(
                SqlAlchemyCurrencyQueryRepository(uow.session)
            )
            result = await handler.execute(ValidateCurrencyQuery(" usd "))
            self.assertEqual(
                (result.code, result.numeric_code, result.minor_units),
                ("USD", "840", 2),
            )
            for code in ("JPY", "ZZZ"):
                with (
                    self.subTest(code=code),
                    self.assertRaises(CurrencyCodeNotSupportedError),
                ):
                    await handler.execute(ValidateCurrencyQuery(code))

    async def test_onboarding_commit_readback_and_http_schema_isolation(self) -> None:
        created = []
        for code in ("USD", "UAH"):
            async with UnitOfWork(self.sessions) as uow:
                handler, _ = self.make_handler(uow.session)
                created.append(await handler.execute(self.make_command(code)))
        tenant_id = TenantIdVO.from_value(created[0].tenant_id)
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, tenant_id.uuid, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                settings = await SqlAlchemyTenantCurrencySettingsRepository(
                    uow.session
                ).get()
                self.assertEqual(settings.base_currency, CurrencyVO("USD"))
                repository = SqlAlchemyTenantCurrencySettingsQueryRepository(
                    uow.session, tenant_id
                )
                self.assertEqual(
                    (await repository.get_currency_settings(tenant_id)).base_currency,
                    "USD",
                )
                self.assertIsNone(
                    await repository.get_currency_settings(
                        TenantIdVO.from_value(created[1].tenant_id)
                    )
                )
        app = FastAPI()
        app.include_router(router, prefix="/api/console")
        app.dependency_overrides[require_authenticated_request_context] = (
            lambda: RequestContext(
                Principal(str(uuid4()), str(tenant_id.uuid), "session", ("member",)),
                None,
                None,
                None,
            )
        )

        async def tenant_uow() -> AsyncGenerator[UnitOfWork, None]:
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, tenant_id.uuid, self.naming)
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    yield uow

        app.dependency_overrides[get_uow] = tenant_uow
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/console/tenants/current/currency-settings",
                params={"tenant_id": str(created[1].tenant_id)},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"base_currency": "USD"})

    async def test_invalid_currency_prevents_all_onboarding_resources(self) -> None:
        for code in ("JPY", "ZZZ"):
            async with UnitOfWork(self.sessions) as uow:
                handler, resources = self.make_handler(uow.session)
                with self.assertRaises(CurrencyCodeNotSupportedError):
                    await handler.execute(self.make_command(code))
                for resource, method in zip(
                    resources, ("register", "create_tenant_admin")
                ):
                    getattr(resource, method).assert_not_awaited()
                self.assertEqual(
                    await uow.session.scalar(
                        text("SELECT count(*) FROM public.tenants")
                    ),
                    0,
                )
                self.assertEqual(
                    await uow.session.scalar(
                        text("SELECT count(*) FROM public.tenant_domains")
                    ),
                    0,
                )
                self.assertEqual(
                    await uow.session.scalar(
                        text(
                            "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'dnk_%'"
                        )
                    ),
                    0,
                )

    async def test_onboarding_schema_and_settings_rollback_and_money_roundtrip(
        self,
    ) -> None:
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            async with UnitOfWork(self.sessions) as uow:
                handler, _ = self.make_handler(uow.session)
                await handler.execute(self.make_command("USD"))
                raise RuntimeError("rollback")
        amount = MoneyVO(Decimal("-999999999999999.9999"), CurrencyVO("USD"))
        async with self.engine.begin() as connection:
            self.assertEqual(
                await connection.scalar(text("SELECT count(*) FROM public.tenants")), 0
            )
            self.assertEqual(
                await connection.scalar(
                    text("SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'dnk_%'")
                ),
                0,
            )
            await connection.execute(
                text(
                    "CREATE TEMP TABLE money_roundtrip (amount NUMERIC(19,4), currency VARCHAR(3))"
                )
            )
            await connection.execute(
                text("INSERT INTO money_roundtrip VALUES (:amount, :currency)"),
                {"amount": amount.amount, "currency": amount.currency.value},
            )
            row = (
                await connection.execute(
                    text("SELECT amount, currency FROM money_roundtrip")
                )
            ).one()
            self.assertEqual(MoneyVO(row.amount, CurrencyVO(row.currency)), amount)

    def make_handler(
        self, session: AsyncSession
    ) -> tuple[CreateTenantHandler, list[AsyncMock]]:
        storage, identity = [AsyncMock() for _ in range(2)]
        identity.create_tenant_admin.return_value = type(
            "Provisioned",
            (),
            {"user_id": uuid4(), "user_email_id": uuid4(), "user_status": "active"},
        )()
        return CreateTenantHandler(
            TenantOnboardingService(
                SqlAlchemyTenantRepository(session),
                SqlAlchemyTenantDomainRepository(session),
            ),
            identity,
            TenantSchemaBootstrapContextFactory(schema_prefix="dnk_"),
            AlembicTenantSchemaBootstrapAdapter(session, TenantMigrator()),
            storage,
            ReferenceDataCurrencyValidator(
                ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(session))
            ),
            TenantCurrencySettingsPersistenceAdapter(session, self.naming),
            CatalogProvisioningAdapter(
                session,
                self.naming,
                CatalogProvisioningFacade(
                    SqlAlchemyProductTypeRepository(session),
                    UUID7Generator(),
                    UtcClock(),
                ),
            ),
        ), [storage, identity]

    def make_command(self, code: str) -> CreateTenantCommand:
        suffix = uuid4().hex
        return CreateTenantCommand(
            tenant_name="Currency test",
            external_id=suffix,
            tenant_domain_host=f"{suffix}.example.test",
            user_first_name="Test",
            user_last_name="Admin",
            user_email="test@example.com",
            base_currency=code,
        )
