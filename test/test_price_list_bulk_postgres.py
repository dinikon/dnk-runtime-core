"""Real PostgreSQL contracts for streaming publication, fencing and keyset queries."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from pathlib import Path

from sqlalchemy import event, select, func, insert, update, delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO
from src.modules.price_lists.domain.price_list.preset import prom_xml_config
from src.modules.price_lists.domain.offer.value_object.values import OfferValues
from src.modules.price_lists.domain.sync_run.error import (
    DuplicateExternalIdError,
    SourceValidationError,
    LostJobLease,
)
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.application.sync_run.dto.parsed_row_dto import ParsedRow
from src.modules.price_lists.application.sync_run.dto.source_dto import FetchResult
from src.modules.price_lists.application.sync_run.command.synchronize_price_list_command import (
    SynchronizePriceListCommand,
)
from src.modules.price_lists.application.sync_run.use_case.synchronize_price_list import (
    SynchronizePriceListUseCase,
)
from src.modules.price_lists.application.offer.query.list_offers_query import (
    ListOffersQuery,
)
from src.modules.price_lists.application.offer.query.offer_history_query import (
    OfferHistoryQuery,
)
from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListModel,
    PartnerOfferModel,
    PartnerOfferStateModel,
    PriceListSyncRunModel,
    PriceListSyncItemModel,
)
from src.modules.price_lists.infrastructure.persistence.offer_repository import (
    SqlAlchemyOfferRepository,
)
from src.modules.price_lists.infrastructure.persistence.query_repository import (
    SqlAlchemyPriceListQueryRepository,
)
from src.modules.price_lists.infrastructure.locking import PostgresPriceListLock
from src.modules.price_lists.infrastructure.calendar import (
    IdentifierGenerator,
    CronCalendar,
)
from src.modules.price_lists.presentation.depends.application import (
    get_background_transactions,
)
from src.modules.price_lists.presentation.depends.infrastructure import (
    get_tenant_naming,
)
from src.modules.shared.application.pagination.errors import InvalidCursorError


class FixtureFetcher:
    @asynccontextmanager
    async def open(self, url):
        yield FetchResult(Path("/unused"), "a" * 64, "text/xml", 100)


class FixtureParser:
    def __init__(self, rows, batch_size=1000):
        self.items = rows
        self.batch_size = batch_size

    async def batches(self, *args, **kwargs):
        for start in range(0, len(self.items), self.batch_size):
            yield self.items[start : start + self.batch_size]


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class PriceListBulkPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], pool_size=12, max_overflow=0
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant_id = EntityIdVO(uuid4())
        self.actor_id = EntityIdVO(uuid4())
        self.price_id = PriceListIdVO(uuid4())
        self.options = ImportOptions(batch_size=1000)
        self.naming = get_tenant_naming()
        self.schema = self.naming.schema_name(self.tenant_id)
        self.execution = {"schema_translate_map": {"tenant": self.schema}}
        self.tables = [
            model.__table__
            for model in (
                PriceListModel,
                PartnerOfferModel,
                PartnerOfferStateModel,
                PriceListSyncRunModel,
                PriceListSyncItemModel,
            )
        ]
        async with self.engine.begin() as connection:
            await connection.run_sync(
                lambda conn: ScheduledJobModel.__table__.create(conn, checkfirst=True)
            )
            await connection.execute(CreateSchema(self.schema))
            await TenantMigrator().upgrade(connection, self.schema)
        self.transactions = get_background_transactions(
            self.sessions, options=self.options
        )
        source, mapping = prom_xml_config()
        now = datetime.now(UTC)
        self.price = PriceList.create(
            price_list_id=self.price_id,
            actor_id=self.actor_id,
            title="Test",
            source_format="xml",
            source_preset=None,
            source_url_secret="encrypted",
            source_url_display="masked",
            source_config=source,
            mapping_config=mapping,
            now=now,
        )
        self.price.status = "active"
        self.price.cron_expression = "0 */6 * * *"
        async with self.transactions() as tx:
            await tx.prices.add(self.tenant_id, self.price)

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(ScheduledJobModel).where(
                    ScheduledJobModel.tenant_id == self.tenant_id.uuid
                )
            )
            await connection.execute(DropSchema(self.schema, cascade=True))
        await self.engine.dispose()

    def row(self, index, price="10", errors=(), rrp="20"):
        value = OfferValues(
            str(index),
            f"SKU-{index}",
            f"Offer {index}",
            Decimal(price),
            None if rrp is None else Decimal(rrp),
            "UAH",
            "in_stock",
            5,
        )
        normalized = {name: getattr(value, name) for name in value.__dataclass_fields__}
        normalized["value_hash"] = value.value_hash
        return ParsedRow(index + 1, normalized, errors)

    async def job(self):
        command = SynchronizePriceListCommand(
            self.tenant_id,
            self.price_id,
            EntityIdVO(uuid4()),
            self.price.schedule_revision,
            "manual",
            datetime.now(UTC),
            "token",
        )
        async with self.sessions() as session:
            await session.execute(
                insert(ScheduledJobModel).values(
                    id=command.job_id.uuid,
                    tenant_id=self.tenant_id.uuid,
                    job_type="price_list.sync",
                    payload={},
                    run_at=command.planned_at,
                    status="running",
                    attempts=1,
                    lock_token="token",
                    locked_until=command.planned_at + timedelta(hours=1),
                )
            )
            await session.commit()
        return command

    def use_case(self, rows, *, parser=None):
        cipher = Mock()
        cipher.decrypt.return_value = "https://example.test/price.xml"
        return SynchronizePriceListUseCase(
            self.transactions,
            FixtureFetcher(),
            parser or FixtureParser(rows, self.options.batch_size),
            cipher,
            CronCalendar(),
            IdentifierGenerator(),
            PostgresPriceListLock(self.sessions),
            UtcClock(),
            self.options,
            Mock(),
        )

    async def apply(self, rows, **policies):
        if policies:
            async with self.transactions() as tx:
                price = await tx.prices.get(self.tenant_id, self.price_id)
                price.update(policies, self.actor_id, datetime.now(UTC))
                await tx.prices.save(self.tenant_id, price)
        command = await self.job()
        count = 0

        def query(*args):
            nonlocal count
            count += 1

        event.listen(self.engine.sync_engine, "before_cursor_execute", query)
        try:
            await self.use_case(rows)(command)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", query)
        async with self.transactions() as tx:
            run = await tx.runs.find_by_job(
                self.tenant_id, self.price_id, command.job_id
            )
        return run, count

    async def count(self, model):
        async with self.sessions() as session:
            return int(
                await session.scalar(
                    select(func.count())
                    .select_from(model.__table__)
                    .execution_options(**self.execution)
                )
            )

    async def query(self, **kwargs):
        async with self.sessions() as session:
            return await SqlAlchemyPriceListQueryRepository(
                session, self.naming, self.options
            ).list_offers(
                ListOffersQuery(tenant_id=self.tenant_id, filters={}, **kwargs)
            )

    async def test_large_import_and_equivalent_repeat_have_bounded_queries(self):
        rows = [self.row(i) for i in range(1005)]
        first, queries = await self.apply(rows)
        self.assertEqual(first.counters["created"], 1005)
        self.assertLess(queries, 60)
        self.assertEqual(await self.count(PartnerOfferModel), 1005)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1005)
        repeated, queries = await self.apply(
            [self.row(i, price="10.0000") for i in range(1005)]
        )
        self.assertEqual(repeated.counters["unchanged"], 1005)
        self.assertEqual(repeated.counters["changed"], 0)
        self.assertLess(queries, 60)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1005)
        self.assertEqual(await self.count(PriceListSyncItemModel), 0)

    async def test_currency_snapshots_survive_rate_revisions_and_repeat_import(self):
        from datetime import date
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from src.modules.currency.infrastructure.persistence.models import CurrencyModel
        from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
            IntegrationOutboxEventModel,
        )
        from src.modules.shared.infrastructure.persistence.unit_of_work import (
            UnitOfWork,
        )
        from src.modules.currency.presentation.depends import build_currency_services
        from src.modules.currency.application.commands import (
            InitializeCurrency,
            SetManualRate,
        )
        from src.modules.currency.domain.models import CurrencyPair, ProviderCode
        from src.modules.price_lists.application.offer.money import OfferMoneyService
        from src.modules.price_lists.infrastructure.persistence.money_snapshot import (
            SqlOfferMoneyRepository,
            OfferMoneySnapshotModel,
        )
        from test.test_currency import USD, EUR, UAH, POLICY

        async with self.engine.begin() as connection:
            for model in (CurrencyModel, IntegrationOutboxEventModel):
                await connection.run_sync(
                    lambda conn, table=model.__table__: table.create(
                        conn, checkfirst=True
                    )
                )
            await connection.execute(
                pg_insert(CurrencyModel.__table__)
                .values(
                    [
                        dict(code=str(code), name=str(code), minor_units=2)
                        for code in (USD, EUR, UAH)
                    ]
                )
                .on_conflict_do_nothing()
            )
        async with UnitOfWork(self.sessions) as uow:
            settings = build_currency_services(
                uow.session, UtcClock(), self.naming
            ).settings
            await settings.initialize(
                InitializeCurrency(
                    self.tenant_id,
                    self.actor_id,
                    replace(POLICY, provider_code=ProviderCode("MANUAL")),
                    (USD, EUR, UAH),
                    UAH,
                    date(2020, 1, 1),
                    "Initial",
                )
            )
            await settings.set_manual_rate(
                SetManualRate(
                    self.tenant_id,
                    self.actor_id,
                    CurrencyPair(USD, UAH),
                    Decimal("40"),
                    date(2020, 1, 1),
                )
            )

        def foreign_row(index, currency):
            values = replace(self.row(index).offer_values(), currency=currency)
            return ParsedRow(
                index + 1,
                {
                    **{
                        name: getattr(values, name)
                        for name in values.__dataclass_fields__
                    },
                    "value_hash": values.value_hash,
                },
                (),
            )

        rows = [foreign_row(0, "USD"), foreign_row(1, "EUR")]
        await self.apply(rows)
        async with self.sessions() as session:
            table = OfferMoneySnapshotModel.__table__
            before = list(
                (
                    await session.execute(
                        select(table).execution_options(**self.execution)
                    )
                ).mappings()
            )
        usd = next(row for row in before if row["status"] == "converted")
        self.assertEqual(Decimal(usd["purchase_price"]["converted"]["amount"]), 400)
        self.assertEqual(Decimal(usd["rrp"]["converted"]["amount"]), 800)
        self.assertEqual(
            next(row for row in before if row["status"] == "unavailable")["error_code"],
            "exchange_rate_not_found",
        )
        async with UnitOfWork(self.sessions) as uow:
            settings = build_currency_services(
                uow.session, UtcClock(), self.naming
            ).settings
            await settings.set_manual_rate(
                SetManualRate(
                    self.tenant_id,
                    self.actor_id,
                    CurrencyPair(USD, UAH),
                    Decimal("42"),
                    date(2020, 1, 1),
                )
            )
            await settings.set_manual_rate(
                SetManualRate(
                    self.tenant_id,
                    self.actor_id,
                    CurrencyPair(EUR, UAH),
                    Decimal("50"),
                    date(2020, 1, 1),
                )
            )
        repeated, _ = await self.apply(rows)
        self.assertEqual(repeated.counters["unchanged"], 2)
        self.assertEqual(await self.count(PartnerOfferStateModel), 2)
        async with self.sessions() as session:
            money = OfferMoneyService(
                build_currency_services(session, UtcClock(), self.naming).facade,
                SqlOfferMoneyRepository(session, self.naming, self.options),
            )
            page = await self.query()
            enriched = await money.enrich(self.tenant_id, page)
            by_currency = {item.currency: item for item in enriched.items}
            self.assertEqual(
                Decimal(
                    by_currency["USD"].current_conversion["purchase_price"][
                        "converted"
                    ]["amount"]
                ),
                420,
            )
            self.assertEqual(
                by_currency["USD"].historical_conversion["purchase_price"],
                usd["purchase_price"],
            )
            self.assertEqual(
                by_currency["EUR"].historical_conversion["status"], "unavailable"
            )
            self.assertEqual(
                by_currency["EUR"].current_conversion["status"], "converted"
            )
            after = list(
                (
                    await session.execute(
                        select(table).execution_options(**self.execution)
                    )
                ).mappings()
            )
            self.assertEqual(before, after)
        async with self.engine.begin() as connection:
            await connection.execute(
                delete(IntegrationOutboxEventModel).where(
                    IntegrationOutboxEventModel.tenant_id == self.tenant_id.uuid
                )
            )

    async def test_missing_reappeared_and_partial_feed(self):
        await self.apply([self.row(0), self.row(1)])
        partial, _ = await self.apply(
            [self.row(0, "12"), self.row(2, errors=("invalid",))], missing_threshold=1
        )
        self.assertEqual(partial.status, "partial")
        self.assertEqual(partial.counters["missing"], 0)
        self.assertEqual(await self.count(PartnerOfferStateModel), 3)
        missing, _ = await self.apply([self.row(0, "12")], missing_threshold=1)
        self.assertEqual(missing.counters["missing"], 1)
        self.assertEqual(await self.count(PartnerOfferStateModel), 4)
        repeated, _ = await self.apply([self.row(0, "12")], missing_threshold=1)
        self.assertEqual(repeated.counters["changed"], 0)
        appeared, _ = await self.apply([self.row(0, "12"), self.row(1)])
        self.assertEqual(appeared.counters["reappeared"], 1)
        self.assertEqual(appeared.counters["changed"], 1)

    async def test_duplicate_across_batches_rejected_without_publication(self):
        rows = [self.row(i) for i in range(1001)]
        rows[-1] = replace(rows[-1], normalized=self.row(0).normalized)
        with self.assertRaises(DuplicateExternalIdError):
            await self.apply(rows)
        self.assertEqual(await self.count(PartnerOfferModel), 0)
        self.assertEqual(await self.count(PartnerOfferStateModel), 0)

    async def test_threshold_failure_leaves_previous_prices_unchanged(self):
        await self.apply([self.row(0)])
        with self.assertRaises(SourceValidationError):
            await self.apply(
                [
                    self.row(0, "12"),
                    self.row(1, errors=("invalid",)),
                    self.row(2, errors=("invalid",)),
                ]
            )
        page = await self.query()
        self.assertEqual(page.items[0].purchase_price, Decimal("10.0000"))
        self.assertEqual(await self.count(PartnerOfferStateModel), 1)

    async def test_quarantine_and_ignore_policies(self):
        run, _ = await self.apply(
            [self.row(0), self.row(1, errors=("invalid",))],
            new_item_policy="quarantine",
        )
        self.assertEqual(run.counters["quarantined"], 1)
        self.assertEqual(await self.count(PriceListSyncItemModel), 1)
        self.assertEqual(await self.count(PartnerOfferModel), 0)
        run, _ = await self.apply([self.row(2)], new_item_policy="ignore")
        self.assertEqual(run.counters["ignored"], 1)
        self.assertEqual(await self.count(PartnerOfferModel), 0)

    async def test_interrupted_publication_rolls_back_all_batches(self):
        original = SqlAlchemyOfferRepository.save_batch
        calls = 0

        async def fail_second(repo, *args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Interrupted publication")
            return await original(repo, *args)

        with patch.object(SqlAlchemyOfferRepository, "save_batch", fail_second):
            with self.assertRaises(RuntimeError):
                await self.apply([self.row(i) for i in range(1005)])
        self.assertEqual(await self.count(PartnerOfferModel), 0)
        self.assertEqual(await self.count(PartnerOfferStateModel), 0)
        self.assertGreater(await self.count(PriceListSyncItemModel), 0)

    async def test_same_job_after_commit_is_idempotent(self):
        command = await self.job()
        use_case = self.use_case([self.row(0)])
        await use_case(command)
        await use_case(command)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1)
        self.assertEqual(await self.count(PriceListSyncRunModel), 1)

    async def test_expired_and_replaced_lease_cannot_publish(self):
        command = await self.job()
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == command.job_id.uuid)
                .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
            )
            await session.commit()
        with self.assertRaises(LostJobLease):
            await self.use_case([self.row(0)])(command)
        self.assertEqual(await self.count(PartnerOfferModel), 0)

    async def test_cursor_ties_nulls_total_and_query_mismatch(self):
        await self.apply([self.row(i, rrp=None if i > 2 else "20") for i in range(6)])
        ids = []
        cursor = None
        while True:
            page = await self.query(
                pagination="cursor", sort="rrp", limit=2, cursor=cursor
            )
            self.assertIsNone(page.total)
            ids.extend(item.id for item in page.items)
            if not page.has_more:
                break
            cursor = page.next_cursor
        self.assertEqual(len(ids), 6)
        self.assertEqual(len(set(ids)), 6)
        with self.assertRaises(InvalidCursorError):
            await self.query(pagination="cursor", sort="title", limit=2, cursor=cursor)
        page = await self.query(pagination="cursor", include_total=True)
        self.assertEqual(page.total, 6)

    async def test_lock_is_pinned_and_released_after_cancellation(self):
        lock = PostgresPriceListLock(self.sessions)
        entered = asyncio.Event()

        async def hold():
            async with lock.hold(self.tenant_id, self.price_id) as acquired:
                self.assertTrue(acquired)
                entered.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(hold())
        await asyncio.wait_for(entered.wait(), 2)
        try:
            async with lock.hold(self.tenant_id, self.price_id) as acquired:
                self.assertFalse(acquired)
            async with lock.hold(self.tenant_id, PriceListIdVO(uuid4())) as acquired:
                self.assertTrue(acquired)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        async with lock.hold(self.tenant_id, self.price_id) as acquired:
            self.assertTrue(acquired)

    async def test_lifecycle_and_lease_changes_before_commit_roll_back(self):
        from src.modules.price_lists.application.price_list.use_case.pause_price_list import (
            PausePriceListUseCase,
        )
        from src.modules.price_lists.application.price_list.command.pause_price_list_command import (
            PausePriceListCommand,
        )

        for action in ("pause", "replace_token"):
            with self.subTest(action=action):
                async with self.transactions() as tx:
                    price = await tx.prices.get(self.tenant_id, self.price_id)
                    price.status = "active"
                    await tx.prices.save(self.tenant_id, price)
                command = await self.job()
                original = SqlAlchemyOfferRepository.save_batch

                async def interrupt(repo, *args):
                    await original(repo, *args)
                    if action == "pause":
                        async with self.transactions() as tx:
                            use_case = PausePriceListUseCase(
                                tx.prices,
                                tx.jobs,
                                CronCalendar(),
                                IdentifierGenerator(),
                                Mock(),
                                Mock(),
                                UtcClock(),
                                tx.runs,
                            )
                            await use_case(
                                PausePriceListCommand(
                                    self.tenant_id, self.actor_id, self.price_id
                                )
                            )
                    else:
                        async with self.sessions() as session:
                            await session.execute(
                                update(ScheduledJobModel)
                                .where(ScheduledJobModel.id == command.job_id.uuid)
                                .values(lock_token="replacement")
                            )
                            await session.commit()

                with patch.object(SqlAlchemyOfferRepository, "save_batch", interrupt):
                    with self.assertRaises(LostJobLease):
                        await asyncio.wait_for(
                            self.use_case([self.row(0)])(command), 10
                        )
                self.assertEqual(await self.count(PartnerOfferModel), 0)
                async with self.transactions() as tx:
                    run = await tx.runs.find_by_job(
                        self.tenant_id, self.price_id, command.job_id
                    )
                    price = await tx.prices.get(self.tenant_id, self.price_id)
                    self.price.schedule_revision = price.schedule_revision
                if action == "pause":
                    self.assertEqual(run.status, "skipped")

    async def test_cancelled_publication_can_restart_and_only_commits_once(self):
        command = await self.job()
        original = SqlAlchemyOfferRepository.save_batch

        async def cancel(repo, *args):
            await original(repo, *args)
            raise asyncio.CancelledError()

        with patch.object(SqlAlchemyOfferRepository, "save_batch", cancel):
            with self.assertRaises(asyncio.CancelledError):
                await self.use_case([self.row(0)])(command)
        self.assertEqual(await self.count(PartnerOfferModel), 0)
        await self.use_case([self.row(0)])(command)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1)
        self.assertEqual(await self.count(PriceListSyncRunModel), 1)

    async def test_cleanup_recovers_crashed_terminal_job_and_retains_diagnostics(self):
        from src.modules.price_lists.application.sync_run.use_case.cleanup_price_list import (
            CleanupPriceListUseCase,
        )
        from src.modules.price_lists.application.sync_run.command.cleanup_price_list_command import (
            CleanupPriceListCommand,
        )
        from src.modules.price_lists.domain.sync_run.entity import SyncRun
        from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO

        command = await self.job()
        cleanup_job = await self.job()
        run = SyncRun.create(
            SyncRunIdVO(uuid4()),
            self.price_id,
            command.job_id,
            "manual",
            command.planned_at,
            command.planned_at,
        )
        async with self.transactions() as tx:
            await tx.runs.add(self.tenant_id, run)
            await tx.staging.append(self.tenant_id, run.id, [self.row(0)])
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(ScheduledJobModel.id == command.job_id.uuid)
                .values(status="failed", lock_token=None)
            )
            await session.commit()
        cleanup = CleanupPriceListUseCase(self.transactions, UtcClock(), self.options)
        await cleanup(
            CleanupPriceListCommand(
                self.tenant_id, cleanup_job.job_id, cleanup_job.lock_token
            )
        )
        async with self.transactions() as tx:
            result = await tx.runs.find_by_job(
                self.tenant_id, self.price_id, command.job_id
            )
        self.assertEqual(result.status, "failed")
        self.assertEqual(await self.count(PriceListSyncItemModel), 1)
        clock = Mock()
        clock.now.return_value = datetime.now(UTC) + timedelta(days=8)
        await CleanupPriceListUseCase(self.transactions, clock, self.options)(
            CleanupPriceListCommand(
                self.tenant_id, cleanup_job.job_id, cleanup_job.lock_token
            )
        )
        self.assertEqual(await self.count(PriceListSyncItemModel), 0)

    async def test_http_contracts_use_authenticated_tenant_and_preserve_lifecycle(self):
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from src.modules.price_lists.presentation.http.router import (
            router,
            offers_router,
        )
        from src.modules.shared.presentation.identity_context.depends import (
            require_authenticated_request_context,
        )
        from src.modules.identity.presentation.http.csrf import require_csrf
        from src.modules.shared.domain.identity_context.request_context import (
            RequestContext,
        )
        from src.modules.shared.domain.identity_context.principal import Principal
        from src.modules.price_lists.presentation.depends.infrastructure import (
            get_source_cipher,
        )
        from src.modules.price_lists.infrastructure.source.secret import SourceUrlCipher
        from cryptography.fernet import Fernet

        app = FastAPI()
        app.state.db = self.sessions
        app.include_router(router)
        app.include_router(offers_router)
        app.dependency_overrides[require_authenticated_request_context] = (
            lambda: RequestContext(
                Principal(str(self.actor_id), str(self.tenant_id), "session", ()),
                None,
                None,
                None,
            )
        )
        app.dependency_overrides[require_csrf] = lambda: None
        app.dependency_overrides[get_source_cipher] = lambda: SourceUrlCipher(
            Fernet.generate_key().decode()
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://test"
        ) as client:
            created = await client.post(
                "/price-lists",
                json=dict(
                    title="New",
                    source_url="https://example.com/prices.xml?token=secret",
                    source_format="xml",
                    source_preset="prom_xml",
                    tenant_id=str(uuid4()),
                ),
            )
            self.assertEqual(created.status_code, 201, created.text)
            identifier = created.json()["id"]
            response = await client.get(f"/price-lists/{identifier}")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("token=secret", response.text)
            self.assertNotIn("source_url_secret", response.text)
            self.assertEqual(response.json()["title"], "New")
            response = await client.post(f"/price-lists/{self.price_id}/pause")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "paused")
            response = await client.get(
                "/price-list-offers", params={"pagination": "cursor"}
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                set(response.json()), {"items", "limit", "next_cursor", "has_more"}
            )
            response = await client.get("/price-list-offers")
            self.assertEqual(
                set(response.json()), {"items", "offset", "limit", "total"}
            )
            response = await client.get(
                "/price-list-offers", params={"cursor": "wrong"}
            )
            self.assertEqual(response.status_code, 422, response.text)
            response = await client.get(f"/price-lists/{uuid4()}")
            self.assertEqual(response.status_code, 404, response.text)

    async def test_publication_visibility_and_cursor_history_order(self):
        await self.apply([self.row(0)])
        original = SqlAlchemyOfferRepository.save_batch

        async def observe(repo, *args):
            await original(repo, *args)
            page = await self.query()
            self.assertEqual(page.items[0].purchase_price, Decimal("10.0000"))
            self.assertEqual(await self.count(PartnerOfferStateModel), 1)

        with patch.object(SqlAlchemyOfferRepository, "save_batch", observe):
            await self.apply([self.row(0, "12")])
        page = await self.query()
        self.assertEqual(page.items[0].purchase_price, Decimal("12.0000"))
        offer_id = page.items[0].id
        async with self.sessions() as session:
            repo = SqlAlchemyPriceListQueryRepository(
                session, self.naming, self.options
            )
            first = await repo.offer_history(
                OfferHistoryQuery(
                    self.tenant_id, offer_id, {}, pagination="cursor", limit=1
                )
            )
            self.assertTrue(first.has_more)
            self.assertIsNone(first.total)
            second = await repo.offer_history(
                OfferHistoryQuery(
                    self.tenant_id,
                    offer_id,
                    {},
                    pagination="cursor",
                    limit=1,
                    cursor=first.next_cursor,
                    include_total=True,
                )
            )
            self.assertFalse(second.has_more)
            self.assertEqual(second.total, 2)
            self.assertNotEqual(first.items[0].id, second.items[0].id)

    async def test_missing_scan_continues_after_a_fully_present_batch(self):
        await self.apply([self.row(i) for i in range(1005)])
        result, _ = await self.apply(
            [self.row(i) for i in range(1000)], missing_threshold=1
        )
        self.assertEqual(result.counters["missing"], 5)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1010)
