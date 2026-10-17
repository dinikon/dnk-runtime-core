"""Global reference catalogs in a disposable PostgreSQL database."""

from datetime import UTC, datetime
import os
import unittest
from uuid import uuid4

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.domain.codes import (
    CountryCode,
    CurrencyCode,
    LocaleCode,
    LocaleRegionCode,
    TimeZoneCode,
)
from src.modules.reference_data.domain.country.record import Country
from src.modules.reference_data.domain.currency.record import Currency
from src.modules.reference_data.domain.locale.record import Locale
from src.modules.reference_data.domain.time_zone.record import TimeZone
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)


class ReferenceDataPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        value = os.environ.get("DNK_TEST_DATABASE_URL")
        if not value:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is required for isolated PostgreSQL tests"
            )
        url = make_url(value).set(drivername="postgresql+asyncpg")
        self.name = "dnk_reference_test_" + uuid4().hex
        self.admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
        async with self.admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.name}"'))
        self.engine = create_async_engine(url.set(database=self.name))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
        self.now = datetime(2026, 10, 5, tzinfo=UTC)

    async def asyncTearDown(self):
        if hasattr(self, "engine"):
            await self.engine.dispose()
            async with self.admin.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{self.name}"'))
            await self.admin.dispose()

    async def test_public_catalogs_idempotence_deactivation_and_rollback(self):
        ua = Country(CountryCode("UA"), "UKR", "804", "Ukraine")
        us = Country(CountryCode("US"), "USA", "840", "United States")
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyCatalogRepository(uow.session)
            await repository.replace_snapshot(
                "countries", SourceSnapshot("test", "1", (ua, us)), self.now
            )
            await repository.replace_snapshot(
                "currencies",
                SourceSnapshot(
                    "test", "1", (Currency(CurrencyCode("UAH"), "980", "Hryvnia", 2),)
                ),
                self.now,
            )
            await repository.replace_snapshot(
                "locales",
                SourceSnapshot(
                    "test",
                    "1",
                    (
                        Locale(
                            LocaleCode("ru-UA"),
                            "ru",
                            None,
                            LocaleRegionCode("UA"),
                            CountryCode("UA"),
                            "Russian (Ukraine)",
                        ),
                        Locale(
                            LocaleCode("sr-Cyrl-XK"),
                            "sr",
                            "Cyrl",
                            LocaleRegionCode("XK"),
                            None,
                            "Serbian (Kosovo)",
                        ),
                    ),
                ),
                self.now,
            )
            await repository.replace_snapshot(
                "time-zones",
                SourceSnapshot(
                    "test",
                    "1",
                    (TimeZone(TimeZoneCode("Europe/Kyiv"), (CountryCode("UA"),)),),
                ),
                self.now,
            )
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyCatalogRepository(uow.session)
            self.assertEqual(
                [item.code for item in await repository.list_countries()], ["UA", "US"]
            )
            locales = await repository.list_locales()
            self.assertEqual([item.code for item in locales], ["ru-UA", "sr-Cyrl-XK"])
            self.assertEqual(locales[0].region_code, "UA")
            self.assertEqual(locales[1].region_code, "XK")
            self.assertIsNone(locales[1].country_code)
            self.assertEqual(
                (await repository.list_time_zones())[0].country_codes, ("UA",)
            )
            await repository.replace_snapshot(
                "countries", SourceSnapshot("test", "2", (us,)), self.now
            )
            await repository.replace_snapshot(
                "countries", SourceSnapshot("test", "2", (us,)), self.now
            )
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyCatalogRepository(uow.session)
            self.assertEqual(
                [item.code for item in await repository.list_countries()], ["US"]
            )
            self.assertEqual((await repository.list_locales())[0].country_code, "UA")
        with self.assertRaises(Exception):
            async with UnitOfWork(self.sessions) as uow:
                repository = SqlAlchemyCatalogRepository(uow.session)
                await repository.replace_snapshot(
                    "currencies",
                    SourceSnapshot(
                        "test",
                        "broken",
                        (Currency(CurrencyCode("USD"), "840", None, 2),),
                    ),
                    self.now,
                )
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyCatalogRepository(uow.session)
            self.assertEqual(
                [item.code for item in await repository.list_currencies()], ["UAH"]
            )
        async with self.engine.connect() as connection:
            tables = await connection.run_sync(
                lambda conn: inspect(conn).get_table_names(schema="public")
            )
            self.assertTrue(
                {
                    "ref_countries",
                    "ref_currencies",
                    "ref_locales",
                    "ref_time_zones",
                    "ref_country_time_zones",
                    "ref_sync_state",
                }
                <= set(tables)
            )
