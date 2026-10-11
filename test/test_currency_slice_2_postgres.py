"""Миграции, атомарная публикация и конкурентность в собственных временных DB."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import importlib.util
from pathlib import Path
from contextlib import asynccontextmanager
from alembic.migration import MigrationContext
from alembic.operations import Operations
import httpx
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.currency.domain.error import OlderExchangeRateSnapshotError
from src.modules.currency.infrastructure.nbu.error import NbuResponseError
from src.modules.currency.infrastructure.persistence.publication_lock import (
    PostgresExchangeRatePublicationLock,
)
from src.modules.currency.infrastructure.persistence.repository import (
    SqlAlchemyExchangeRateBookRepository,
)
from src.modules.currency.presentation.management.refresh import refresh_exchange_rates
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.handler import (
    GetCurrencyValidationCatalogHandler,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.query import (
    GetCurrencyValidationCatalogQuery,
)
from src.modules.reference_data.infrastructure.currency.persistence.validation_catalog_repository import (
    SqlAlchemyCurrencyValidationCatalogQueryRepository,
)
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from test.test_currency_slice_2 import Clock, NOW, body
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable


async def apply_book_migration(connection, schema, *, downgrade=False):
    spec = importlib.util.spec_from_file_location(
        "currency_book_migration",
        Path(__file__).resolve().parents[1]
        / "migrations/tenant/versions/0024_currency_exchange_rates.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    await connection.execute(
        text("SELECT set_config('search_path', :schema, true)"), {"schema": schema}
    )

    def run(conn):
        with Operations.context(MigrationContext.configure(conn)):
            (migration.downgrade if downgrade else migration.upgrade)()

    await connection.run_sync(run)
    await connection.execute(text("SELECT set_config('search_path', 'public', true)"))


class CurrencySliceTwoPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        value = os.environ.get("DNK_TEST_DATABASE_URL")
        if not value:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is required for isolated PostgreSQL DBs"
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
        self.tenant_id = uuid4()
        self.other_tenant_id = uuid4()
        self.schema = self.naming.schema_name(EntityIdVO.from_value(self.tenant_id))
        self.other_schema = self.naming.schema_name(
            EntityIdVO.from_value(self.other_tenant_id)
        )
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for tenant_id, schema in (
                (self.tenant_id, self.schema),
                (self.other_tenant_id, self.other_schema),
            ):
                await connection.execute(
                    text(
                        "INSERT INTO public.tenants (id,name,external_id) VALUES (:id,'Test',:external_id)"
                    ),
                    {"id": str(tenant_id), "external_id": str(tenant_id)},
                )
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await apply_book_migration(connection, schema)
            await connection.execute(
                text(
                    "INSERT INTO public.ref_currencies (code,numeric_code,name,minor_units,active) VALUES ('USD','840','Dollar',2,true),('UAH','980','Hryvnia',2,true),('XAU','959','Gold',NULL,true),('EUR','978','Euro',2,false)"
                )
            )

    async def drop_database(self) -> None:
        await self.engine.dispose()
        async with self.admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE "{self.name}"'))
        await self.admin.dispose()

    @asynccontextmanager
    async def tenant_sessions(self, tenant_id=None):
        async with self.engine.connect() as connection:
            await bind_tenant_schema(
                connection, tenant_id or self.tenant_id, self.naming
            )
            yield async_sessionmaker(connection, expire_on_commit=False)

    async def read_book(self, tenant_id=None):
        async with (
            self.tenant_sessions(tenant_id) as sessions,
            UnitOfWork(sessions) as uow,
        ):
            return await SqlAlchemyExchangeRateBookRepository(uow.session).get()

    async def refresh(
        self, *, content: str | None = None, seconds: int = 0, tenant_id=None
    ):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text=content or body())
            )
        ) as client:
            return await refresh_exchange_rates(
                self.sessions,
                tenant_id=tenant_id or self.tenant_id,
                naming=self.naming,
                client=client,
                clock=Clock(
                    NOW + timedelta(seconds=seconds),
                    NOW + timedelta(seconds=seconds + 1),
                ),
            )

    async def test_migration_columns_constraints_downgrade_and_reupgrade(self) -> None:
        async with self.engine.begin() as connection:
            columns = await connection.run_sync(
                lambda conn: inspect(conn).get_columns(
                    "currency_exchange_rate_quotes", schema=self.schema
                )
            )
            rate = next(column for column in columns if column["name"] == "rate")
            self.assertEqual((rate["type"].precision, rate["type"].scale), (38, 18))
            self.assertFalse(rate["nullable"])
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema=self.schema)
            )
            self.assertIn("currency_exchange_rate_books", tables)
            await apply_book_migration(connection, self.schema, downgrade=True)
            self.assertIsNone(
                await connection.scalar(
                    text(
                        f"SELECT to_regclass('{self.schema}.currency_exchange_rate_books')"
                    )
                )
            )
            self.assertEqual(
                await connection.scalar(
                    text("SELECT count(*) FROM public.ref_currencies")
                ),
                4,
            )
            await apply_book_migration(connection, self.schema)
            self.assertEqual(
                await connection.scalar(
                    text(
                        f'SELECT count(*) FROM "{self.schema}".currency_exchange_rate_books'
                    )
                ),
                0,
            )
        result = await self.refresh()
        self.assertIsNotNone(result.snapshot_id)
        from sqlalchemy.exc import IntegrityError

        for sql in (
            f"UPDATE {self.schema}.currency_exchange_rate_quotes SET rate = 0",
            f"UPDATE {self.schema}.currency_exchange_rate_quotes SET target_currency = 'USD'",
            f"UPDATE {self.schema}.currency_exchange_rate_books SET source = 'xxx'",
        ):
            with self.assertRaises(IntegrityError):
                async with self.engine.begin() as connection:
                    await connection.execute(text(sql))

    async def test_first_load_confirmation_changes_and_exact_roundtrip(self) -> None:
        first = await self.refresh()
        stored = await self.read_book()
        self.assertEqual(stored.quotes[0].rate, Decimal("41.123456789012345678"))
        self.assertEqual(stored.snapshot_id.uuid, first.snapshot_id)
        confirmed = await self.refresh(seconds=2)
        self.assertEqual(first.snapshot_id, confirmed.snapshot_id)
        self.assertGreater(confirmed.checked_at, first.checked_at)
        changed = await self.refresh(content=body(amount="42"), seconds=4)
        self.assertNotEqual(first.snapshot_id, changed.snapshot_id)
        self.assertEqual((await self.read_book()).quotes[0].rate, Decimal("42"))

    async def test_http_finishes_before_first_sql_and_batch_catalog_filters(
        self,
    ) -> None:
        statements: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany) -> None:
            statements.append(statement)

        active_transactions = set()

        def begin(conn):
            active_transactions.add(conn)

        def end(conn):
            active_transactions.discard(conn)

        event.listen(self.engine.sync_engine, "begin", begin)
        event.listen(self.engine.sync_engine, "commit", end)
        event.listen(self.engine.sync_engine, "rollback", end)
        event.listen(self.engine.sync_engine, "before_cursor_execute", record)

        def respond(request: httpx.Request) -> httpx.Response:
            self.assertFalse(
                any(
                    "currency_exchange_rate_" in statement
                    or "ref_currencies" in statement
                    for statement in statements
                )
            )
            self.assertEqual(active_transactions, set())
            mixed = (
                body()[:-1]
                + ","
                + body(code="XAU", numeric="959")[1:-1]
                + ","
                + body(code="EUR", numeric="978")[1:]
            )
            return httpx.Response(200, text=mixed)

        try:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as client:
                result = await refresh_exchange_rates(
                    self.sessions,
                    tenant_id=self.tenant_id,
                    naming=self.naming,
                    client=client,
                    clock=Clock(NOW, NOW + timedelta(seconds=1)),
                )
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", record)
            event.remove(self.engine.sync_engine, "begin", begin)
            event.remove(self.engine.sync_engine, "commit", end)
            event.remove(self.engine.sync_engine, "rollback", end)
        self.assertEqual(
            (
                result.quote_count,
                result.excluded_metal_count,
                result.excluded_unknown_count,
            ),
            (1, 1, 1),
        )
        async with UnitOfWork(self.sessions) as uow:
            catalog = GetCurrencyValidationCatalogHandler(
                SqlAlchemyCurrencyValidationCatalogQueryRepository(uow.session)
            )
            result = await catalog.execute(
                GetCurrencyValidationCatalogQuery(("USD", "EUR", "ZZZ", "XAU"))
            )
            self.assertEqual(result.missing_codes, ("EUR", "ZZZ"))
            self.assertEqual({item.code for item in result.currencies}, {"USD", "XAU"})

    async def test_failure_and_partial_write_rollback_preserve_previous_book(
        self,
    ) -> None:
        await self.refresh()
        previous = await self.read_book()
        with self.assertRaises(NbuResponseError):
            await self.refresh(content=body(amount="0"), seconds=2)
        self.assertEqual(await self.read_book(), previous)
        from sqlalchemy.ext.asyncio import AsyncSession

        real_execute = AsyncSession.execute

        async def fail_quote_insert(session, statement, *args, **kwargs):
            if (
                statement.is_insert
                and getattr(statement.table, "name", None)
                == "currency_exchange_rate_quotes"
            ):
                raise RuntimeError("Injected after book update and quote deletion")
            return await real_execute(session, statement, *args, **kwargs)

        with (
            patch.object(AsyncSession, "execute", fail_quote_insert),
            self.assertRaises(RuntimeError),
        ):
            await self.refresh(content=body(amount="42"), seconds=2)
        self.assertEqual(await self.read_book(), previous)
        async with self.engine.begin() as connection:
            count = await connection.scalar(
                text(
                    f'SELECT count(*) FROM "{self.schema}".currency_exchange_rate_quotes'
                )
            )
            self.assertEqual(count, 1)

    async def test_lock_serializes_first_load_and_is_released_by_rollback(self) -> None:
        async with (
            self.tenant_sessions() as first_sessions,
            self.tenant_sessions() as second_sessions,
            first_sessions() as first,
            second_sessions() as second,
        ):
            await PostgresExchangeRatePublicationLock(first, self.tenant_id).acquire()
            started = asyncio.Event()

            async def wait_lock() -> None:
                started.set()
                await PostgresExchangeRatePublicationLock(
                    second, self.tenant_id
                ).acquire()

            waiting = asyncio.create_task(wait_lock())
            try:
                await started.wait()
                done, _ = await asyncio.wait({waiting}, timeout=0.1)
                self.assertFalse(done)
                await first.rollback()
                await asyncio.wait_for(waiting, timeout=5)
                self.assertIsNone(
                    await SqlAlchemyExchangeRateBookRepository(second).get()
                )
            finally:
                waiting.cancel()
                await asyncio.gather(waiting, return_exceptions=True)
                await second.rollback()

    async def test_concurrent_first_load_rejects_late_older_result(self) -> None:
        entered = asyncio.Event()
        release = asyncio.Event()

        async def delayed(request: httpx.Request) -> httpx.Response:
            entered.set()
            await release.wait()
            return httpx.Response(200, text=body(amount="40"))

        async with httpx.AsyncClient(transport=httpx.MockTransport(delayed)) as client:
            older = asyncio.create_task(
                refresh_exchange_rates(
                    self.sessions,
                    tenant_id=self.tenant_id,
                    naming=self.naming,
                    client=client,
                    clock=Clock(NOW, NOW + timedelta(seconds=10)),
                )
            )
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                newer = await self.refresh(content=body(amount="42"), seconds=2)
                release.set()
                with self.assertRaises(OlderExchangeRateSnapshotError):
                    await older
                stored = await self.read_book()
                self.assertEqual(stored.snapshot_id.uuid, newer.snapshot_id)
                self.assertEqual(stored.quotes[0].rate, Decimal("42"))
            finally:
                release.set()
                older.cancel()
                await asyncio.gather(older, return_exceptions=True)

    async def test_uncommitted_replacement_is_invisible_and_success_logged_after_commit(
        self,
    ) -> None:
        await self.refresh()
        previous = await self.read_book()
        entered = asyncio.Event()
        release = asyncio.Event()
        real_save = SqlAlchemyExchangeRateBookRepository.save

        async def pause_after_save(repository, value) -> None:
            await real_save(repository, value)
            entered.set()
            await release.wait()

        with (
            patch.object(
                SqlAlchemyExchangeRateBookRepository, "save", pause_after_save
            ),
            patch(
                "src.modules.currency.presentation.management.refresh.logger.info"
            ) as log,
        ):
            updating = asyncio.create_task(
                self.refresh(content=body(amount="43"), seconds=2)
            )
            try:
                await asyncio.wait_for(entered.wait(), timeout=5)
                self.assertEqual(await self.read_book(), previous)
                log.assert_not_called()
                release.set()
                await updating
                log.assert_called_once()
                self.assertEqual((await self.read_book()).quotes[0].rate, Decimal("43"))
            finally:
                release.set()
                updating.cancel()
                await asyncio.gather(updating, return_exceptions=True)

    async def test_commit_failure_rolls_back_and_does_not_log_success(self) -> None:
        await self.refresh()
        previous = await self.read_book()
        with (
            patch.object(
                UnitOfWork, "commit", side_effect=RuntimeError("commit failed")
            ),
            patch(
                "src.modules.currency.presentation.management.refresh.logger.info"
            ) as log,
        ):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                await self.refresh(content=body(amount="44"), seconds=2)
            log.assert_not_called()
        self.assertEqual(await self.read_book(), previous)

    async def test_tenant_isolation_and_independent_publication_locks(self) -> None:
        first = await self.refresh()
        self.assertIsNone(await self.read_book(self.other_tenant_id))
        second = await self.refresh(
            content=body(amount="55"), tenant_id=self.other_tenant_id
        )
        self.assertNotEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(
            (await self.read_book()).quotes[0].rate, Decimal("41.123456789012345678")
        )
        self.assertEqual(
            (await self.read_book(self.other_tenant_id)).quotes[0].rate, Decimal("55")
        )
        async with self.sessions() as one, self.sessions() as two:
            await PostgresExchangeRatePublicationLock(one, self.tenant_id).acquire()
            await asyncio.wait_for(
                PostgresExchangeRatePublicationLock(
                    two, self.other_tenant_id
                ).acquire(),
                timeout=2,
            )
            await one.rollback()
            await two.rollback()
        async with self.engine.connect() as connection:
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema="public")
            )
            self.assertNotIn("currency_exchange_rate_books", tables)
            self.assertNotIn("currency_exchange_rate_quotes", tables)

    async def test_missing_and_deleting_tenant_rejected_before_http(self) -> None:
        async def no_http(request):
            self.fail("NBU must not be called for unavailable tenant")

        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE public.tenants SET status='deletion_pending' WHERE id=:id"
                ),
                {"id": str(self.tenant_id)},
            )
        async with httpx.AsyncClient(transport=httpx.MockTransport(no_http)) as client:
            for tenant_id in (uuid4(), self.tenant_id):
                with self.assertRaises(TenantUnavailable):
                    await refresh_exchange_rates(
                        self.sessions,
                        client=client,
                        tenant_id=tenant_id,
                        naming=self.naming,
                        clock=Clock(NOW),
                    )

    async def test_full_tenant_migration_chain_registers_currency(self) -> None:
        schema = "dnk_" + uuid4().hex
        async with self.engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await TenantMigrator().upgrade(connection, schema)
            self.assertEqual(
                await TenantMigrator().current(connection, schema),
                ("0024_currency_exchange_rates",),
            )
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema=schema)
            )
            self.assertIn("currency_exchange_rate_books", tables)
            self.assertIn("currency_exchange_rate_quotes", tables)
