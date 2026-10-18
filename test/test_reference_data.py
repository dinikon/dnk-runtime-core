"""Public catalog source parsing, synchronization, and HTTP contracts."""

from datetime import UTC, datetime
from io import BytesIO
import tarfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
import httpx
from httpx import ASGITransport, AsyncClient, MockTransport, Response

from src.modules.identity.presentation.auth.depends import (
    get_optional_request_context,
    require_authenticated_request_context,
)
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.reference_data.application.port.catalog import SourceSnapshot
from src.modules.reference_data.application.sync.handler import (
    InvalidSourceSnapshotError,
    SyncReferenceDataHandler,
)
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
from src.modules.reference_data.domain.locale.subtags import parse_locale_subtags
from src.modules.reference_data.domain.time_zone.record import TimeZone
from src.modules.reference_data.infrastructure.country.source import CldrCountrySource
from src.modules.reference_data.infrastructure.locale.source import CldrLocaleSource
from src.modules.reference_data.infrastructure.time_zone.source import (
    IanaTimeZoneSource,
)
from src.modules.reference_data.infrastructure.currency.source import SixCurrencySource
from src.modules.reference_data.presentation.depends import get_catalog_repository
from src.modules.reference_data.presentation.jobs.refresh import (
    ensure_weekly_jobs,
    weekly_window,
)
from src.modules.reference_data.presentation.router import router
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.infrastructure.jobs.worker import ScheduledJobWorker


class StubClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 5, tzinfo=UTC)


class StubSource:
    def __init__(self, snapshot: SourceSnapshot) -> None:
        self.snapshot = snapshot

    async def fetch(self) -> SourceSnapshot:
        return self.snapshot


class StubRepository:
    def __init__(self) -> None:
        self.writes = []

    async def last_count(self, dataset: str) -> int | None:
        return None

    async def replace_snapshot(self, *args) -> None:
        self.writes.append(args)

    async def list_countries(self):
        return [Country(CountryCode("UA"), "UKR", "804", "Ukraine")]

    async def list_currencies(self):
        return [Currency(CurrencyCode("UAH"), "980", "Hryvnia", 2)]

    async def list_locales(self):
        return [
            Locale(
                LocaleCode("ru-UA"),
                "ru",
                None,
                LocaleRegionCode("UA"),
                CountryCode("UA"),
                "Russian (Ukraine)",
            )
        ]

    async def list_time_zones(self):
        return [TimeZone(TimeZoneCode("Europe/Kyiv"), (CountryCode("UA"),))]


class CldrStub:
    async def version(self):
        return "48.2.0"

    async def read(self, version, path):
        if path.endswith("codeMappings.json"):
            return {
                "supplemental": {
                    "codeMappings": {
                        "UA": {"_alpha3": "UKR", "_numeric": "804"},
                        "EU": {"_alpha3": "QUU", "_numeric": "967"},
                    }
                }
            }
        if path.endswith("territoryInfo.json"):
            return {"supplemental": {"territoryInfo": {"UA": {}, "EU": {}}}}
        if path.endswith("territories.json"):
            return {
                "main": {
                    "en": {
                        "localeDisplayNames": {
                            "territories": {
                                "UA": "Ukraine",
                                "EU": "European Union",
                                "XK": "Kosovo",
                                "419": "Latin America",
                            }
                        }
                    }
                }
            }
        if path.endswith("languages.json"):
            return {
                "main": {
                    "en": {
                        "localeDisplayNames": {
                            "languages": {
                                "uk": "Ukrainian",
                                "ru": "Russian",
                                "sr": "Serbian",
                                "es": "Spanish",
                            }
                        }
                    }
                }
            }
        if path.endswith("availableLocales.json"):
            return {
                "availableLocales": {
                    "full": ["uk", "ru", "sr-Cyrl", "sr-Cyrl-XK", "sr-Latn", "es-419"]
                }
            }
        raise AssertionError(path)


class ReferenceDataTests(unittest.IsolatedAsyncioTestCase):
    async def test_cldr_codes_and_required_regional_locales(self):
        country = await CldrCountrySource(CldrStub()).fetch()
        locale = await CldrLocaleSource(CldrStub()).fetch()
        self.assertEqual(
            country.records, (Country(CountryCode("UA"), "UKR", "804", "Ukraine"),)
        )
        self.assertIn(
            Locale(
                LocaleCode("ru-UA"),
                "ru",
                None,
                LocaleRegionCode("UA"),
                CountryCode("UA"),
                "Russian (Ukraine)",
            ),
            locale.records,
        )
        self.assertIn(
            Locale(
                LocaleCode("uk-UA"),
                "uk",
                None,
                LocaleRegionCode("UA"),
                CountryCode("UA"),
                "Ukrainian (Ukraine)",
            ),
            locale.records,
        )
        self.assertIn(
            Locale(
                LocaleCode("sr-Cyrl-XK"),
                "sr",
                "Cyrl",
                LocaleRegionCode("XK"),
                None,
                "Serbian (Kosovo)",
            ),
            locale.records,
        )
        self.assertIn(
            Locale(
                LocaleCode("es-419"),
                "es",
                None,
                LocaleRegionCode("419"),
                None,
                "Spanish (Latin America)",
            ),
            locale.records,
        )

    def test_regionless_locale_codes_are_parsed_independently_of_country(self):
        self.assertEqual(parse_locale_subtags("uk"), ("uk", None, None))
        self.assertEqual(parse_locale_subtags("sr-Latn"), ("sr", "Latn", None))
        self.assertEqual(parse_locale_subtags("sr-Cyrl-XK"), ("sr", "Cyrl", "XK"))
        self.assertEqual(parse_locale_subtags("es-419"), ("es", None, "419"))

    async def test_six_deduplicates_country_rows(self):
        xml = b'<ISO_4217 Pblshd="2026-10-05"><CcyTbl><CcyNtry><CcyNm>Hryvnia</CcyNm><Ccy>UAH</Ccy><CcyNbr>980</CcyNbr><CcyMnrUnts>2</CcyMnrUnts></CcyNtry><CcyNtry><CcyNm>Hryvnia</CcyNm><Ccy>UAH</Ccy><CcyNbr>980</CcyNbr><CcyMnrUnts>2</CcyMnrUnts></CcyNtry></CcyTbl></ISO_4217>'
        async with httpx.AsyncClient(
            transport=MockTransport(lambda request: Response(200, content=xml))
        ) as client:
            result = await SixCurrencySource(client).fetch()
        self.assertEqual(
            result.records, (Currency(CurrencyCode("UAH"), "980", "Hryvnia", 2),)
        )

    async def test_iana_preserves_multi_country_zone(self):
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, data in (
                (
                    "zone1970.tab",
                    b"UA\t+5026+03031\tEurope/Kyiv\nCH,DE\t+4723+00832\tEurope/Zurich\n",
                ),
                (
                    "zone.tab",
                    b"UA\t+5026+03031\tEurope/Kyiv\nUA\t+4900+03100\tEurope/Uzhgorod\n",
                ),
                ("version", b"2026c\n"),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, BytesIO(data))
        async with httpx.AsyncClient(
            transport=MockTransport(
                lambda request: Response(200, content=buffer.getvalue())
            )
        ) as client:
            result = await IanaTimeZoneSource(client).fetch()
        self.assertIn(
            TimeZone(
                TimeZoneCode("Europe/Zurich"), (CountryCode("CH"), CountryCode("DE"))
            ),
            result.records,
        )
        self.assertIn(
            TimeZone(TimeZoneCode("Europe/Kyiv"), (CountryCode("UA"),)), result.records
        )
        self.assertIn(
            TimeZone(TimeZoneCode("Europe/Uzhgorod"), (CountryCode("UA"),)),
            result.records,
        )

    async def test_incomplete_snapshot_never_reaches_repository(self):
        repository = StubRepository()
        snapshot = SourceSnapshot(
            "test", "1", (Country(CountryCode("UA"), "UKR", "804", "Ukraine"),)
        )
        handler = SyncReferenceDataHandler(
            "countries", StubSource(snapshot), repository, StubClock()
        )
        with self.assertRaises(InvalidSourceSnapshotError):
            await handler.execute()
        self.assertEqual(repository.writes, [])

    async def test_four_read_only_routes(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/console")
        repository = StubRepository()
        regional_locales = await repository.list_locales()
        repository.list_locales = AsyncMock(
            return_value=[
                Locale(LocaleCode("uk"), "uk", None, None, None, "Ukrainian"),
                *regional_locales,
            ]
        )
        app.dependency_overrides[get_catalog_repository] = lambda: repository
        app.dependency_overrides[require_authenticated_request_context] = (
            lambda: object()
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            base = "/api/console/reference-data"
            for path in ("countries", "currencies", "locales", "time-zones"):
                response = await client.get(f"{base}/{path}")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()), 1)
                self.assertEqual((await client.post(f"{base}/{path}")).status_code, 405)
            self.assertEqual(
                (await client.get(f"{base}/time-zones")).json()[0]["country_codes"],
                ["UA"],
            )
            locales = (await client.get(f"{base}/locales")).json()
            self.assertEqual([item["code"] for item in locales], ["uk"])
            self.assertIsNone(locales[0]["region_code"])

    async def test_read_routes_require_authentication(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/console")
        app.dependency_overrides[get_optional_request_context] = lambda: RequestContext(
            None, None, None, None
        )
        app.dependency_overrides[get_catalog_repository] = lambda: StubRepository()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for path in ("countries", "currencies", "locales", "time-zones"):
                response = await client.get(f"/api/console/reference-data/{path}")
                self.assertEqual(response.status_code, 401)

    def test_weekly_window(self):
        self.assertEqual(
            weekly_window(datetime(2026, 10, 5, 2, 59, tzinfo=UTC)),
            datetime(2026, 9, 28, 3, tzinfo=UTC),
        )
        self.assertEqual(
            weekly_window(datetime(2026, 10, 5, 3, tzinfo=UTC)),
            datetime(2026, 10, 5, 3, tzinfo=UTC),
        )

    async def test_weekly_registration_is_global_and_deterministic(self):
        class Result:
            def all(self):
                return []

        class Session:
            async def execute(self, statement):
                return Result()

        class FakeUow:
            session = Session()

            def __init__(self, factory):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        schedule = AsyncMock()
        now = datetime(2026, 10, 5, 12, tzinfo=UTC)
        with (
            patch(
                "src.modules.reference_data.presentation.jobs.refresh.UnitOfWork",
                FakeUow,
            ),
            patch(
                "src.modules.reference_data.presentation.jobs.refresh.build_schedule_scheduled_job_use_case",
                return_value=schedule,
            ),
        ):
            await ensure_weekly_jobs(object(), now)
            first = [call.args[0] for call in schedule.await_args_list]
            schedule.reset_mock()
            await ensure_weekly_jobs(object(), now)
            second = [call.args[0] for call in schedule.await_args_list]
        self.assertEqual(first, second)
        self.assertEqual(
            [item.payload["dataset"] for item in first],
            ["countries", "currencies", "locales", "time-zones"],
        )
        self.assertTrue(all(item.tenant_id is None for item in first))
        self.assertTrue(
            all(item.run_at == datetime(2026, 10, 5, 3, tzinfo=UTC) for item in first)
        )

    async def test_global_job_dispatch_skips_tenant_gate(self):
        worker = object.__new__(ScheduledJobWorker)
        worker.dispatcher = type("Dispatcher", (), {"dispatch": AsyncMock()})()
        worker.tenant_gate = type(
            "Gate", (), {"hold": lambda *args: self.fail("TenantGate called")}
        )()
        now = datetime(2026, 10, 5, tzinfo=UTC)
        job = ScheduledJob(
            uuid4(),
            None,
            "reference_data.refresh",
            {"dataset": "countries"},
            now,
            "scheduled",
            0,
            None,
            None,
            now,
            now,
        )
        await worker._dispatch(job)
        worker.dispatcher.dispatch.assert_awaited_once_with(job)
