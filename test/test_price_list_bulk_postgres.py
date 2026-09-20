"""Bulk-import contracts against a disposable PostgreSQL database."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
import os
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from src.modules.price_lists.domain import canonical_state_hash
from src.modules.price_lists.infrastructure.persistence.models import (
    PriceListModel,
    PartnerOfferModel,
    PartnerOfferStateModel,
    PriceListSyncRunModel,
    PriceListSyncItemModel,
)
from src.modules.price_lists.infrastructure.persistence.repository import (
    SqlAlchemyPriceListRepository,
)
from src.modules.price_lists.infrastructure.source import ParsedRow
from src.modules.price_lists.presentation.jobs.handler import PriceListSyncJobHandler


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class PriceListBulkPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(os.environ["TEST_POSTGRES_URL"])
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.tenant_id, self.actor_id = uuid4(), uuid4()
        async with self.sessions() as session:
            self.options = SqlAlchemyPriceListRepository(session)._options(
                self.tenant_id
            )
        self.schema = self.options["schema_translate_map"]["tenant"]
        self.tables = [
            m.__table__
            for m in (
                PriceListModel,
                PartnerOfferModel,
                PartnerOfferStateModel,
                PriceListSyncRunModel,
                PriceListSyncItemModel,
            )
        ]
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(self.schema))
            await connection.execution_options(**self.options)
            await connection.run_sync(
                lambda conn: PriceListModel.metadata.create_all(
                    conn, tables=self.tables
                )
            )
        async with self.sessions() as session:
            repo = SqlAlchemyPriceListRepository(session)
            self.price_id = await repo.create(
                tenant_id=self.tenant_id,
                actor_id=self.actor_id,
                title="Test",
                source_format="xml",
                source_preset=None,
                source_url="test",
                source_url_display="test",
                source_config={},
                mapping_config={},
            )
            self.price = await repo.get(self.tenant_id, self.price_id)
            await session.commit()

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.execute(DropSchema(self.schema, cascade=True))
        await self.engine.dispose()

    def row(self, index, price="10", errors=()):
        normalized = dict(
            external_id=str(index),
            sku=f"SKU-{index}",
            title=f"Offer {index}",
            purchase_price=Decimal(price),
            rrp=Decimal("20"),
            currency="UAH",
            availability="in_stock",
            quantity=5,
        )
        normalized["value_hash"] = canonical_state_hash(
            **{
                k: normalized[k]
                for k in (
                    "purchase_price",
                    "rrp",
                    "currency",
                    "availability",
                    "quantity",
                )
            }
        )
        return ParsedRow(row_number=index + 1, normalized=normalized, errors=errors)

    async def apply(self, rows, **policies):
        async with self.sessions() as session:
            repo = SqlAlchemyPriceListRepository(session)
            run_id = await repo.create_run(
                tenant_id=self.tenant_id,
                price_list_id=self.price_id,
                trigger="manual",
                scheduled_job_id=uuid4(),
                planned_at=datetime.now(UTC),
            )
            await session.commit()
            count = 0

            def query(*args):
                nonlocal count
                count += 1

            event.listen(self.engine.sync_engine, "before_cursor_execute", query)
            start = time.monotonic()
            try:
                result = await repo.apply_rows(
                    tenant_id=self.tenant_id,
                    actor_id=self.actor_id,
                    price_list=self.price | policies,
                    run_id=run_id,
                    rows=rows,
                )
                await session.commit()
            finally:
                event.remove(self.engine.sync_engine, "before_cursor_execute", query)
            return result, count, time.monotonic() - start

    async def count(self, model):
        async with self.sessions() as session:
            return await session.scalar(
                select(func.count())
                .select_from(model.__table__)
                .execution_options(**self.options)
            )

    async def test_large_import_and_unchanged_repeat_use_bounded_query_counts(self):
        rows = [self.row(i) for i in range(1005)]
        first, queries, _ = await self.apply(rows)
        self.assertEqual(first["created"], 1005)
        self.assertLessEqual(queries, 10)
        self.assertEqual(await self.count(PartnerOfferModel), 1005)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1005)
        repeat, queries, _ = await self.apply(rows)
        self.assertEqual(repeat["unchanged"], 1005)
        self.assertEqual(repeat["changed"], 0)
        self.assertLessEqual(queries, 7)
        self.assertEqual(await self.count(PartnerOfferStateModel), 1005)
        self.assertEqual(await self.count(PriceListSyncItemModel), 0)

    async def test_changed_missing_and_reappeared_states_keep_history(self):
        await self.apply([self.row(0), self.row(1)])
        changed, _, _ = await self.apply([self.row(0, "12")], missing_threshold=1)
        self.assertEqual(changed["changed"], 2)
        self.assertEqual(changed["missing"], 1)
        self.assertEqual(await self.count(PartnerOfferStateModel), 4)
        repeat, _, _ = await self.apply([self.row(0, "12")], missing_threshold=1)
        self.assertEqual(repeat["changed"], 0)
        await self.apply(
            [self.row(0, "12")], missing_item_policy="archive", missing_threshold=1
        )
        returned, _, _ = await self.apply([self.row(0, "12"), self.row(1)])
        self.assertEqual(returned["reappeared"], 1)
        self.assertEqual(returned["changed"], 1)
        async with self.sessions() as session:
            offers = (
                (
                    await session.execute(
                        select(PartnerOfferModel.__table__).execution_options(
                            **self.options
                        )
                    )
                )
                .mappings()
                .all()
            )
        self.assertTrue(
            all(
                o["current_state_id"] and o["lifecycle_status"] == "active"
                for o in offers
            )
        )

    async def test_quarantine_ignore_and_rejected_rows(self):
        counters, _, _ = await self.apply(
            [self.row(0), self.row(1, errors=("invalid",))],
            new_item_policy="quarantine",
        )
        self.assertEqual(counters["quarantined"], 1)
        self.assertEqual(counters["rejected"], 1)
        self.assertEqual(await self.count(PartnerOfferModel), 0)
        self.assertEqual(await self.count(PriceListSyncItemModel), 1)
        counters, _, _ = await self.apply([self.row(2)], new_item_policy="ignore")
        self.assertEqual(counters["ignored"], 1)
        self.assertEqual(await self.count(PartnerOfferModel), 0)

    async def test_failure_rolls_back_all_offer_and_state_batches(self):
        with patch.object(
            SqlAlchemyPriceListRepository,
            "_update_many",
            side_effect=RuntimeError("interrupted"),
        ):
            with self.assertRaises(RuntimeError):
                await self.apply([self.row(i) for i in range(1005)])
        self.assertEqual(await self.count(PartnerOfferModel), 0)
        self.assertEqual(await self.count(PartnerOfferStateModel), 0)
        self.assertEqual(await self.count(PriceListSyncItemModel), 0)

    async def test_lock_is_pinned_across_commits_and_released_after_cancellation(self):
        handler = PriceListSyncJobHandler(self.sessions)
        entered = asyncio.Event()

        async def hold():
            async with handler._price_list_lock(
                self.tenant_id, self.price_id
            ) as acquired:
                self.assertTrue(acquired)
                entered.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(hold())
        await asyncio.wait_for(entered.wait(), 2)
        try:
            async with handler._price_list_lock(
                self.tenant_id, self.price_id
            ) as acquired:
                self.assertFalse(acquired)
            async with handler._price_list_lock(self.tenant_id, uuid4()) as acquired:
                self.assertTrue(acquired)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        async with handler._price_list_lock(self.tenant_id, self.price_id) as acquired:
            self.assertTrue(acquired)
