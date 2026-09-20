"""Currency integration checks create databases only under TEST_POSTGRES_URL."""

import asyncio
from dataclasses import replace
from datetime import date
from decimal import Decimal
import os
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import unittest

from sqlalchemy import text, select, func
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.schema import CreateSchema

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.currency.presentation.depends import build_currency_services
from src.modules.currency.application.commands import (
    InitializeCurrency,
    ConfigureCurrencyPolicy,
    SetManualRate,
    ScheduleFunctionalCurrencyChange,
    SetEnabledCurrency,
)
from src.modules.currency.application.provider import (
    ProviderRateDTO,
    SyncProviderRates,
    ExchangeRateProviderRegistry,
)
from src.modules.currency.infrastructure.persistence.provider_writer import (
    ProviderImportTransactions,
    GlobalProviderRateWriter,
)
from src.modules.currency.infrastructure.persistence.models import (
    CurrencyModel,
    ManualExchangeRateModel,
    RateImportModel,
    ProviderRateModel,
    FunctionalCurrencyPeriodModel,
)
from src.modules.currency.domain.models import CurrencyPair, ProviderCode
from src.modules.currency.domain.errors import CurrencyConflict
from test.test_currency import USD, EUR, UAH, POLICY, NOW, DAY, FRIDAY


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"),
    "Set TEST_POSTGRES_URL to a disposable PostgreSQL 16 database.",
)
class CurrencyPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.url = make_url(os.environ["TEST_POSTGRES_URL"]).set(
            drivername="postgresql+asyncpg"
        )
        self.database = "dnk_currency_" + uuid4().hex
        self.admin = create_async_engine(self.url, isolation_level="AUTOCOMMIT")
        async with self.admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.database}"'))
        self.engine = create_async_engine(self.url.set(database=self.database))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.clock = SimpleNamespace(now=lambda: NOW)
        self.naming = TenantSchemaNaming("dnk_")
        self.tenants = [EntityIdVO(uuid4()), EntityIdVO(uuid4())]
        self.actor = EntityIdVO(uuid4())
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for tenant in self.tenants:
                schema = self.naming.schema_name(tenant)
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)

    async def asyncTearDown(self):
        if hasattr(self, "engine"):
            await self.engine.dispose()
        async with self.admin.connect() as connection:
            await connection.execute(
                text(f'DROP DATABASE "{self.database}" WITH (FORCE)')
            )
        await self.admin.dispose()

    def services(self, session):
        return build_currency_services(session, self.clock, self.naming)

    async def initialize(self, tenant=None):
        tenant = tenant or self.tenants[0]
        async with UnitOfWork(self.sessions) as uow:
            await self.services(uow.session).settings.initialize(
                InitializeCurrency(
                    tenant,
                    self.actor,
                    replace(POLICY, provider_code=ProviderCode("MANUAL")),
                    (USD, EUR, UAH),
                    UAH,
                    date(2020, 1, 1),
                    "Initial",
                )
            )

    async def test_migrations_seed_repeat_and_downgrade(self):
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            count = await connection.scalar(
                select(func.count()).select_from(CurrencyModel.__table__)
            )
            self.assertGreater(count, 160)
            schema = self.naming.schema_name(self.tenants[0])
            await TenantMigrator().upgrade(connection, schema)
            await TenantMigrator().downgrade(
                connection, schema, "0006_price_list_streaming"
            )
            self.assertIsNone(
                await connection.scalar(
                    text("SELECT to_regclass(:name)"),
                    {"name": schema + ".currency_policy"},
                )
            )
            await TenantMigrator().upgrade(connection, schema)

    async def test_scope_conversions_and_rollback(self):
        for tenant in self.tenants:
            await self.initialize(tenant)
        async with UnitOfWork(self.sessions) as uow:
            services = self.services(uow.session)
            for tenant, value in zip(self.tenants, ("40", "50"), strict=True):
                await services.settings.set_manual_rate(
                    SetManualRate(
                        tenant,
                        self.actor,
                        CurrencyPair(USD, UAH),
                        Decimal(value),
                        FRIDAY,
                    )
                )
            a = await services.facade.convert_to_functional(
                tenant_id=self.tenants[0], money=Money(100, USD), business_date=DAY
            )
            b = await services.facade.convert_to_functional(
                tenant_id=self.tenants[1], money=Money(100, USD), business_date=DAY
            )
            self.assertEqual(
                (a.converted.amount, b.converted.amount), (Decimal(4000), Decimal(5000))
            )
        with self.assertRaises(RuntimeError):
            async with UnitOfWork(self.sessions) as uow:
                await self.services(uow.session).settings.set_manual_rate(
                    SetManualRate(
                        self.tenants[0],
                        self.actor,
                        CurrencyPair(USD, UAH),
                        Decimal(99),
                        FRIDAY,
                    )
                )
                raise RuntimeError("Abort consumer transaction")
        async with UnitOfWork(self.sessions) as uow:
            history = await self.services(uow.session).rates.history(
                tenant_id=self.tenants[0], provider=ProviderCode("MANUAL")
            )
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].rate, 40)

    async def test_concurrent_revisions_and_optimistic_lock(self):
        await self.initialize()
        tenant = self.tenants[0]

        async def set_rate(value):
            async with UnitOfWork(self.sessions) as uow:
                return await self.services(uow.session).settings.set_manual_rate(
                    SetManualRate(
                        tenant, self.actor, CurrencyPair(USD, UAH), Decimal(value), DAY
                    )
                )

        await asyncio.gather(set_rate("40"), set_rate("41"))
        async with UnitOfWork(self.sessions) as uow:
            services = self.services(uow.session)
            rows = await services.rates.history(
                tenant_id=tenant, provider=ProviderCode("MANUAL")
            )
            self.assertEqual(sorted(r.revision for r in rows), [1, 2])
            self.assertEqual(sum(r.is_current for r in rows), 1)
            await services.settings.configure(
                ConfigureCurrencyPolicy(tenant, self.actor, POLICY, 1)
            )
        with self.assertRaises(CurrencyConflict):
            async with UnitOfWork(self.sessions) as uow:
                await self.services(uow.session).settings.configure(
                    ConfigureCurrencyPolicy(tenant, self.actor, POLICY, 1)
                )

    async def test_cross_common_date_and_future_period_protection(self):
        await self.initialize()
        tenant = self.tenants[0]
        async with UnitOfWork(self.sessions) as uow:
            services = self.services(uow.session)
            for source, value, day in (
                (USD, "40", FRIDAY),
                (EUR, "50", FRIDAY),
                (USD, "42", DAY),
            ):
                await services.settings.set_manual_rate(
                    SetManualRate(
                        tenant,
                        self.actor,
                        CurrencyPair(source, UAH),
                        Decimal(value),
                        day,
                    )
                )
            result = await services.facade.convert(
                tenant_id=tenant, money=Money(100, USD), target=EUR, date=DAY
            )
            self.assertEqual(result.converted.amount, 80)
            self.assertEqual(result.conversion.effective_date, FRIDAY)
            await services.settings.schedule(
                ScheduleFunctionalCurrencyChange(
                    tenant, self.actor, EUR, date(2027, 1, 1), "Change"
                )
            )
            self.assertEqual(
                await services.facade.get_functional_currency(
                    tenant_id=tenant, business_date=date(2026, 12, 31)
                ),
                UAH,
            )
            self.assertEqual(
                await services.facade.get_functional_currency(
                    tenant_id=tenant, business_date=date(2027, 1, 1)
                ),
                EUR,
            )
        with self.assertRaises(CurrencyConflict):
            async with UnitOfWork(self.sessions) as uow:
                await self.services(uow.session).settings.set_enabled(
                    SetEnabledCurrency(tenant, self.actor, EUR, False)
                )
        with self.assertRaises(IntegrityError):
            async with self.engine.begin() as connection:
                await connection.execute(
                    FunctionalCurrencyPeriodModel.__table__.insert()
                    .values(
                        id=uuid4(),
                        currency_code="USD",
                        valid_from=date(2025, 1, 1),
                        valid_to=None,
                        created_at=NOW,
                        created_by=self.actor.uuid,
                        reason="Overlap",
                    )
                    .execution_options(
                        schema_translate_map={"tenant": self.naming.schema_name(tenant)}
                    )
                )

    async def test_provider_repeated_revision_and_failure_audit(self):
        adapter = SimpleNamespace(code=ProviderCode("NBU"))
        rows = [ProviderRateDTO(CurrencyPair(USD, UAH), Decimal("40"), DAY)]

        async def fetch(**kwargs):
            return rows

        adapter.fetch = fetch
        registry = ExchangeRateProviderRegistry()
        registry.register(adapter)
        service = SyncProviderRates(
            registry, ProviderImportTransactions(self.sessions), self.clock
        )
        args = dict(provider=ProviderCode("NBU"), start_date=DAY, end_date=DAY)
        self.assertEqual((await service(**args))["created_count"], 1)
        self.assertEqual((await service(**args))["created_count"], 0)
        results = await asyncio.gather(service(**args), service(**args))
        self.assertTrue(
            all(r["created_count"] == r["updated_count"] == 0 for r in results)
        )
        rows[0] = replace(rows[0], rate=Decimal("41"))
        self.assertEqual((await service(**args))["updated_count"], 1)
        original = GlobalProviderRateWriter.save_many

        async def fail_after_write(writer, **kwargs):
            await original(writer, **kwargs)
            raise RuntimeError("Simulated publication failure")

        rows[0] = replace(rows[0], rate=Decimal("42"))
        with (
            patch.object(GlobalProviderRateWriter, "save_many", fail_after_write),
            self.assertRaises(RuntimeError),
        ):
            await service(**args)
        async with self.engine.connect() as connection:
            table = ProviderRateModel.__table__
            self.assertEqual(
                await connection.scalar(select(func.count()).select_from(table)), 2
            )
            self.assertEqual(
                await connection.scalar(select(table.c.rate).where(table.c.is_current)),
                41,
            )
            imports = RateImportModel.__table__
            self.assertEqual(
                await connection.scalar(
                    select(func.count())
                    .select_from(imports)
                    .where(imports.c.status == "failed")
                ),
                1,
            )
