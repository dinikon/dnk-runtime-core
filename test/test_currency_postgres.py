from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.currency.application.provider.command.sync_provider_rates_command import (
    SyncProviderRatesCommand,
)
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO

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
from test.currency_support import fixture_components
from src.modules.currency.application.settings.command.initialize_currency_command import (
    InitializeCurrency,
)
from src.modules.currency.application.policy.command.configure_currency_policy_command import (
    ConfigureCurrencyPolicy,
)
from src.modules.currency.application.manual_rate.command.set_manual_rate_command import (
    SetManualRate,
)
from src.modules.currency.application.functional_currency.command.schedule_functional_currency_change_command import (
    ScheduleFunctionalCurrencyChange,
)
from src.modules.currency.application.enabled_currency.command.set_enabled_currency_command import (
    SetEnabledCurrency,
)
from src.modules.currency.application.provider.dto.provider_rate_dto import (
    ProviderRateDTO,
)
from src.modules.currency.application.provider.use_case.sync_provider_rates import (
    SyncProviderRates,
)
from src.modules.currency.application.provider.registry import (
    ExchangeRateProviderRegistry,
)
from src.modules.currency.infrastructure.persistence.rate_import.transactions import (
    ProviderImportTransactions,
)
from src.modules.currency.infrastructure.persistence.provider_rate.writer import (
    GlobalProviderRateWriter,
)
from src.modules.currency.infrastructure.persistence.directory.model import (
    CurrencyModel,
)
from src.modules.currency.infrastructure.persistence.manual_rate.model import (
    ManualExchangeRateModel,
)
from src.modules.currency.infrastructure.persistence.rate_import.model import (
    RateImportModel,
)
from src.modules.currency.infrastructure.persistence.provider_rate.model import (
    ProviderRateModel,
)
from src.modules.currency.infrastructure.persistence.functional_currency.model import (
    FunctionalCurrencyPeriodModel,
)
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.policy.error import CurrencyConflict
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
        return fixture_components(session, self.clock, self.naming)

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
                    id=FunctionalCurrencyPeriodIdVO(uuid4()),
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
                        id=ManualExchangeRateIdVO(uuid4()),
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
                        id=ManualExchangeRateIdVO(uuid4()),
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
                        tenant,
                        self.actor,
                        CurrencyPair(USD, UAH),
                        Decimal(value),
                        DAY,
                        id=ManualExchangeRateIdVO(uuid4()),
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
                        id=ManualExchangeRateIdVO(uuid4()),
                    )
                )
            result = await services.facade.convert(
                tenant_id=tenant, money=Money(100, USD), target=EUR, date=DAY
            )
            self.assertEqual(result.converted.amount, 80)
            self.assertEqual(result.conversion.effective_date, FRIDAY)
            await services.settings.schedule(
                ScheduleFunctionalCurrencyChange(
                    tenant,
                    self.actor,
                    EUR,
                    date(2027, 1, 1),
                    "Change",
                    id=FunctionalCurrencyPeriodIdVO(uuid4()),
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
        self.assertEqual(
            (
                await service(SyncProviderRatesCommand(RateImportIdVO(uuid4()), **args))
            ).created_count,
            1,
        )
        self.assertEqual(
            (
                await service(SyncProviderRatesCommand(RateImportIdVO(uuid4()), **args))
            ).created_count,
            0,
        )
        results = await asyncio.gather(
            service(SyncProviderRatesCommand(RateImportIdVO(uuid4()), **args)),
            service(SyncProviderRatesCommand(RateImportIdVO(uuid4()), **args)),
        )
        self.assertTrue(all(r.created_count == r.updated_count == 0 for r in results))
        rows[0] = replace(rows[0], rate=Decimal("41"))
        self.assertEqual(
            (
                await service(SyncProviderRatesCommand(RateImportIdVO(uuid4()), **args))
            ).updated_count,
            1,
        )
        original = GlobalProviderRateWriter.save_many

        async def fail_after_write(writer, **kwargs):
            await original(writer, **kwargs)
            raise RuntimeError("Simulated publication failure")

        rows[0] = replace(rows[0], rate=Decimal("42"))
        with (
            patch.object(GlobalProviderRateWriter, "save_many", fail_after_write),
            self.assertRaises(RuntimeError),
        ):
            await service(SyncProviderRatesCommand(RateImportIdVO(uuid4()), **args))
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

    async def test_noop_settings_and_manual_rate_preserve_versions_and_events(self):
        from src.modules.currency.infrastructure.persistence.policy.model import (
            CurrencyPolicyModel,
        )
        from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
            IntegrationOutboxEventModel,
        )

        await self.initialize()
        tenant = self.tenants[0]
        command = SetManualRate(
            tenant,
            self.actor,
            CurrencyPair(USD, UAH),
            Decimal("40"),
            DAY,
            ManualExchangeRateIdVO(uuid4()),
        )
        async with UnitOfWork(self.sessions) as uow:
            services = self.services(uow.session)
            first = await services.settings.set_manual_rate(command)
            second = await services.settings.set_manual_rate(command)
            third = await services.settings.set_manual_rate(
                replace(command, id=ManualExchangeRateIdVO(uuid4()))
            )
            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertFalse(third.created)
            self.assertEqual(first.rate.id, third.rate.id)
        execution = {
            "schema_translate_map": {"tenant": self.naming.schema_name(tenant)}
        }
        async with self.sessions() as session:
            before = (
                (
                    await session.execute(
                        select(CurrencyPolicyModel.__table__).execution_options(
                            **execution
                        )
                    )
                )
                .mappings()
                .one()
            )
            events_before = await session.scalar(
                select(func.count()).select_from(IntegrationOutboxEventModel)
            )
        async with UnitOfWork(self.sessions) as uow:
            services = self.services(uow.session)
            current = await services.policies.get(tenant_id=tenant)
            result = await services.settings.configure(
                ConfigureCurrencyPolicy(tenant, self.actor, current, 1)
            )
            self.assertEqual(result.version, 1)
            await services.settings.set_enabled(
                SetEnabledCurrency(tenant, self.actor, USD, True)
            )
        async with self.sessions() as session:
            after = (
                (
                    await session.execute(
                        select(CurrencyPolicyModel.__table__).execution_options(
                            **execution
                        )
                    )
                )
                .mappings()
                .one()
            )
            self.assertEqual(dict(before), dict(after))
            self.assertEqual(
                events_before,
                await session.scalar(
                    select(func.count()).select_from(IntegrationOutboxEventModel)
                ),
            )
        with self.assertRaises(CurrencyConflict):
            async with UnitOfWork(self.sessions) as uow:
                await self.services(uow.session).settings.configure(
                    ConfigureCurrencyPolicy(tenant, self.actor, current, 2)
                )

    async def test_resolution_audit_survives_rollback_and_deduplicates_operations(self):
        from src.modules.currency.infrastructure.persistence.resolution_failure.model import (
            ResolutionFailureModel,
        )
        from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
            IntegrationOutboxEventModel,
        )
        from src.modules.currency.application.conversion.dto.conversion_request import (
            ConversionRequest,
        )
        from src.modules.currency.application.conversion.dto.unavailable_conversion import (
            UnavailableConversion,
        )
        from src.modules.currency.presentation.depends.application import (
            build_currency_components,
        )

        await self.initialize()
        tenant, operation = self.tenants[0], EntityIdVO(uuid4())
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                async with UnitOfWork(self.sessions) as uow:
                    c = build_currency_components(
                        uow.session,
                        self.clock,
                        self.naming,
                        session_factory=self.sessions,
                        operation_id=operation,
                    )
                    result = await c.facade.convert_many(
                        tenant_id=tenant,
                        items=[ConversionRequest(Money(10, USD), DAY, UAH)] * 100,
                    )
                    self.assertTrue(
                        all(isinstance(r, UnavailableConversion) for r in result)
                    )
                    raise RuntimeError("Rollback importing transaction")
        async with self.sessions() as session:
            rows = (
                (
                    await session.execute(
                        select(ResolutionFailureModel.__table__).execution_options(
                            schema_translate_map={
                                "tenant": self.naming.schema_name(tenant)
                            }
                        )
                    )
                )
                .mappings()
                .all()
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["operation_id"], operation.uuid)
            table = IntegrationOutboxEventModel.__table__
            self.assertEqual(
                await session.scalar(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.event_type == "RateResolutionFailed")
                ),
                1,
            )

    async def test_activation_delayed_retry_and_timezone_replanning(self):
        from datetime import datetime, timezone
        from src.modules.currency.presentation.depends.application import (
            get_activate_functional_currency_use_case,
        )
        from src.modules.currency.application.functional_currency.command.activate_functional_currency_command import (
            ActivateFunctionalCurrencyCommand,
        )
        from src.modules.shared.infrastructure.jobs.scheduled_job_model import (
            ScheduledJobModel,
        )
        from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
            IntegrationOutboxEventModel,
        )

        await self.initialize()
        tenant = self.tenants[0]
        async with UnitOfWork(self.sessions) as uow:
            s = self.services(uow.session)
            period = await s.settings.schedule(
                ScheduleFunctionalCurrencyChange(
                    tenant,
                    self.actor,
                    EUR,
                    date(2027, 1, 1),
                    "Next",
                    FunctionalCurrencyPeriodIdVO(uuid4()),
                )
            )
            policy = await s.policies.get(tenant_id=tenant)
            await s.settings.configure(
                ConfigureCurrencyPolicy(
                    tenant,
                    self.actor,
                    replace(policy, business_timezone="America/New_York"),
                    1,
                )
            )
        async with self.sessions() as session:
            jobs = (
                (await session.execute(select(ScheduledJobModel.__table__)))
                .mappings()
                .all()
            )
            active = [j for j in jobs if j["status"] == "scheduled"]
            self.assertEqual(len(active), 1)
            self.assertEqual(
                active[0]["run_at"], datetime(2027, 1, 1, 5, tzinfo=timezone.utc)
            )
        # An obsolete/early job cannot announce the change before the new timezone's midnight.
        self.clock.now = lambda: datetime(2027, 1, 1, 0, tzinfo=timezone.utc)
        async with UnitOfWork(self.sessions) as uow:
            await get_activate_functional_currency_use_case(
                self.services(uow.session).components
            )(ActivateFunctionalCurrencyCommand(tenant, period.id))
        self.clock.now = lambda: datetime(2027, 1, 3, 10, tzinfo=timezone.utc)
        for _ in range(2):
            async with UnitOfWork(self.sessions) as uow:
                await get_activate_functional_currency_use_case(
                    self.services(uow.session).components
                )(ActivateFunctionalCurrencyCommand(tenant, period.id))
        async with self.sessions() as session:
            table = IntegrationOutboxEventModel.__table__
            events = (
                (
                    await session.execute(
                        select(table).where(
                            table.c.event_type == "FunctionalCurrencyActivated"
                        )
                    )
                )
                .mappings()
                .all()
            )
            self.assertEqual(
                len(events), 2
            )  # initial past period and exactly one scheduled period
            event = next(e for e in events if e["aggregate_id"] == period.id.uuid)
            self.assertEqual(event["payload"]["effective_date"], "2027-01-01")
            self.assertEqual(
                event["payload"]["activated_at"], "2027-01-03T10:00:00+00:00"
            )

    async def test_display_currency_required_and_policy_snapshot_frozen(self):
        from src.modules.currency.application.settings.reader import (
            OperationCurrencySettings,
        )

        await self.initialize()
        tenant = self.tenants[0]
        async with UnitOfWork(self.sessions) as uow:
            s = self.services(uow.session)
            reader = OperationCurrencySettings(s.policies)
            first = await reader.get(tenant_id=tenant)
            await s.settings.configure(
                ConfigureCurrencyPolicy(
                    tenant,
                    self.actor,
                    replace(first.to_entity(), default_display_currency=EUR),
                    1,
                )
            )
            self.assertEqual(await reader.get(tenant_id=tenant), first)
        with self.assertRaises(CurrencyConflict):
            async with UnitOfWork(self.sessions) as uow:
                await self.services(uow.session).settings.set_enabled(
                    SetEnabledCurrency(tenant, self.actor, EUR, False)
                )

    async def test_concurrent_period_planning_has_one_winner(self):
        from src.modules.currency.domain.functional_currency.error import (
            FunctionalCurrencyChangeNotAllowed,
        )

        await self.initialize()
        tenant = self.tenants[0]

        async def schedule(currency):
            async with UnitOfWork(self.sessions) as uow:
                return await self.services(uow.session).settings.schedule(
                    ScheduleFunctionalCurrencyChange(
                        tenant,
                        self.actor,
                        currency,
                        date(2027, 1, 1),
                        "Concurrent",
                        FunctionalCurrencyPeriodIdVO(uuid4()),
                    )
                )

        results = await asyncio.gather(
            schedule(EUR), schedule(USD), return_exceptions=True
        )
        self.assertEqual(
            sum(isinstance(r, FunctionalCurrencyChangeNotAllowed) for r in results), 1
        )
        async with UnitOfWork(self.sessions) as uow:
            periods = await self.services(uow.session).periods.list_periods(
                tenant_id=tenant
            )
            self.assertEqual(len(periods), 2)
            self.assertEqual(periods[0].valid_to, date(2026, 12, 31))

    async def test_actual_seed_execution_and_global_currency_downgrade(self):
        import importlib.util
        from pathlib import Path
        from alembic import command

        migration_path = Path("migrations/global/versions/0006_currency.py")
        spec = importlib.util.spec_from_file_location(
            "currency_seed_revision_test", migration_path
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        async with self.engine.begin() as connection:
            before = (
                (
                    await connection.execute(
                        select(CurrencyModel.__table__).order_by(
                            CurrencyModel.__table__.c.code
                        )
                    )
                )
                .mappings()
                .all()
            )

            def repeat_seed(conn):
                # Execute the actual migration seed twice, isolating its already-applied DDL.
                with (
                    patch.object(migration.op, "create_table"),
                    patch.object(migration.op, "create_index"),
                    patch.object(migration.op, "get_bind", return_value=conn),
                ):
                    migration.upgrade()
                    migration.upgrade()

            await connection.run_sync(repeat_seed)
            after = (
                (
                    await connection.execute(
                        select(CurrencyModel.__table__).order_by(
                            CurrencyModel.__table__.c.code
                        )
                    )
                )
                .mappings()
                .all()
            )
            self.assertEqual(before, after)
            config = GlobalMigrator().config()

            def downgrade(conn):
                config.attributes["connection"] = conn
                command.downgrade(config, "0005_access_roles")

            await connection.run_sync(downgrade)
            self.assertIsNone(
                await connection.scalar(text("SELECT to_regclass('public.currency')"))
            )
            await GlobalMigrator().upgrade(connection)
            self.assertEqual(
                await connection.scalar(
                    select(func.count()).select_from(CurrencyModel.__table__)
                ),
                len(before),
            )

    async def test_quote_query_count_depends_on_pairs_not_rows(self):
        from sqlalchemy import event
        from src.modules.currency.application.conversion.dto.conversion_request import (
            ConversionRequest,
        )
        from src.modules.currency.domain.policy.value_object.rate_date_policy import (
            RateDatePolicy,
        )
        from src.modules.currency.domain.exchange_rate.error import CrossRateUnavailable

        await self.initialize()
        tenant = self.tenants[0]
        async with UnitOfWork(self.sessions) as uow:
            s = self.services(uow.session)
            await s.settings.set_manual_rate(
                SetManualRate(
                    tenant,
                    self.actor,
                    CurrencyPair(USD, UAH),
                    Decimal("40"),
                    FRIDAY,
                    ManualExchangeRateIdVO(uuid4()),
                )
            )
            await s.settings.set_manual_rate(
                SetManualRate(
                    tenant,
                    self.actor,
                    CurrencyPair(EUR, UAH),
                    Decimal("50"),
                    FRIDAY,
                    ManualExchangeRateIdVO(uuid4()),
                )
            )

        async def count(size):
            statements = []

            def track(conn, cursor, statement, parameters, context, many):
                statements.append(statement)

            event.listen(self.engine.sync_engine, "before_cursor_execute", track)
            try:
                async with UnitOfWork(self.sessions) as uow:
                    s = self.services(uow.session)
                    results = await s.facade.convert_many(
                        tenant_id=tenant,
                        items=[ConversionRequest(Money(100, USD), DAY, EUR)] * size,
                    )
                    self.assertTrue(all(r.converted.amount == 80 for r in results))
            finally:
                event.remove(self.engine.sync_engine, "before_cursor_execute", track)
            return len(statements)

        self.assertEqual(await count(1), await count(1000))
        async with UnitOfWork(self.sessions) as uow:
            s = self.services(uow.session)
            current = await s.policies.get(tenant_id=tenant)
            await s.settings.configure(
                ConfigureCurrencyPolicy(
                    tenant,
                    self.actor,
                    replace(current, rate_date_policy=RateDatePolicy.EXACT),
                    1,
                )
            )
        with self.assertRaises(CrossRateUnavailable):
            async with UnitOfWork(self.sessions) as uow:
                await self.services(uow.session).facade.resolve_rate(
                    tenant_id=tenant, source=USD, target=EUR, date=DAY
                )

    async def test_restore_activation_command_repairs_and_rearms_jobs_idempotently(
        self,
    ):
        import importlib
        from sqlalchemy import insert, update, delete
        from src.modules.shared.infrastructure.jobs.scheduled_job_model import (
            ScheduledJobModel,
        )
        from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel

        module = importlib.import_module(
            "src.modules.currency.presentation.management.restore_activations"
        )
        tenant = self.tenants[0]
        await self.initialize(tenant)
        async with self.engine.begin() as connection:
            await connection.execute(
                insert(TenantModel.__table__).values(
                    id=tenant.uuid,
                    name="Restore test",
                    external_id=str(tenant),
                    status="active",
                )
            )
        async with UnitOfWork(self.sessions) as uow:
            await self.services(uow.session).settings.schedule(
                ScheduleFunctionalCurrencyChange(
                    tenant,
                    self.actor,
                    EUR,
                    date(2030, 1, 1),
                    "Restore",
                    FunctionalCurrencyPeriodIdVO(uuid4()),
                )
            )
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.tenant_id == tenant.uuid
                )
            )
        helper = SimpleNamespace(session_factory=self.sessions, engine=self.engine)
        with (
            patch.object(module, "db_helper", helper),
            patch.object(module, "UtcClock", return_value=self.clock),
        ):
            self.assertEqual(
                await module.restore_activations(
                    SimpleNamespace(tenant_id=tenant.uuid)
                ),
                0,
            )
            self.assertEqual(
                await module.restore_activations(
                    SimpleNamespace(tenant_id=tenant.uuid)
                ),
                0,
            )
        async with self.engine.begin() as connection:
            table = ScheduledJobModel.__table__
            self.assertEqual(
                await connection.scalar(select(func.count()).select_from(table)), 1
            )
            await connection.execute(
                update(table).values(
                    status="failed", attempts=5, last_error="Retry exhausted"
                )
            )
        with (
            patch.object(module, "db_helper", helper),
            patch.object(module, "UtcClock", return_value=self.clock),
        ):
            self.assertEqual(
                await module.restore_activations(
                    SimpleNamespace(tenant_id=tenant.uuid)
                ),
                0,
            )
        async with self.engine.connect() as connection:
            row = (
                (await connection.execute(select(ScheduledJobModel.__table__)))
                .mappings()
                .one()
            )
            self.assertEqual(row["status"], "scheduled")
            self.assertEqual(row["attempts"], 0)
            self.assertIsNone(row["last_error"])
