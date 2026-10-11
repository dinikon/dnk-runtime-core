"""Домен, NBU-контракт, batch-справочник и orchestration второго валютного среза."""

import argparse
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, Inexact, localcontext
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from src.modules.currency.application.command.refresh_exchange_rates.command import (
    RefreshExchangeRatesCommand,
)
from src.modules.currency.application.command.refresh_exchange_rates.handler import (
    RefreshExchangeRatesHandler,
)
from src.modules.currency.application.error import (
    ExchangeRateCatalogMismatchError,
    ExchangeRateSourceError,
)
from src.modules.currency.application.port.catalog import ExchangeRateCurrencyDTO
from src.modules.currency.application.port.source import (
    SourceExchangeRateDTO,
    SourceExchangeRateSnapshotDTO,
)
from src.modules.currency.domain.aggregate import ExchangeRateBook
from src.modules.currency.domain.error import (
    InvalidExchangeRateError,
    InvalidExchangeRateSnapshotError,
    OlderExchangeRateSnapshotError,
)
from src.modules.currency.domain.value_object.quote import ExchangeRateQuoteVO
from src.modules.currency.infrastructure.nbu.source import (
    NbuExchangeRateSource,
    NBU_URL,
)
from src.modules.currency.infrastructure.nbu.error import (
    NbuResponseError,
    NbuTransportError,
    NbuHttpError,
    NbuRateLimitError,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.handler import (
    GetCurrencyValidationCatalogHandler,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.query import (
    GetCurrencyValidationCatalogQuery,
)
from src.modules.reference_data.application.currency.query.get_currency_validation_catalog.dto import (
    GetCurrencyValidationCatalogRecordDTO,
)
from src.modules.currency.infrastructure.adapter.currency_catalog import (
    ReferenceDataExchangeRateCurrencyCatalog,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO

DAY = date(2026, 10, 11)
NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)


class Clock:
    """Управляемые часы без доступа к системному времени."""

    def __init__(self, *values: datetime) -> None:
        self.values = iter(values)

    def now(self) -> datetime:
        return next(self.values)


def quote(code: str = "USD", rate: str = "41") -> ExchangeRateQuoteVO:
    return ExchangeRateQuoteVO(CurrencyVO(code), Decimal(rate))


def book() -> ExchangeRateBook:
    return ExchangeRateBook.create(
        effective_date=DAY,
        request_started_at=NOW,
        checked_at=NOW + timedelta(seconds=1),
        quotes=(quote(),),
    )


def body(
    *,
    code: str = "USD",
    numeric: str = "840",
    amount: str = "41.123456789012345678",
    units: str = "1",
    day: str = "11.10.2026",
) -> str:
    return (
        '[{"CurrencyCodeL":"'
        + code
        + '","CurrencyCode":"'
        + numeric
        + '","Amount":'
        + amount
        + ',"Units":'
        + units
        + ',"StartDate":"'
        + day
        + '"}]'
    )


class ExchangeRateBookTests(unittest.TestCase):
    def test_quote_precision_rounding_range_and_immutability(self) -> None:
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            item = quote(rate="41.1234567890123456785")
        self.assertEqual(item.rate, Decimal("41.123456789012345679"))
        with self.assertRaises(FrozenInstanceError):
            item.rate = Decimal(1)
        for value in (
            "0",
            "-1",
            "NaN",
            "Infinity",
            "1e20",
            "1e-30",
            "99999999999999999999.9999999999999999995",
        ):
            with self.subTest(value=value), self.assertRaises(InvalidExchangeRateError):
                quote(rate=value)

    def test_create_restore_and_confirmation_keep_snapshot_identifier(self) -> None:
        initial = book()
        restored = ExchangeRateBook.restore(
            snapshot_id=initial.snapshot_id,
            effective_date=initial.effective_date,
            request_started_at=initial.request_started_at,
            checked_at=initial.checked_at,
            quotes=initial.quotes,
        )
        self.assertEqual(initial, restored)
        restored.refresh(
            effective_date=DAY,
            request_started_at=NOW + timedelta(seconds=2),
            checked_at=NOW + timedelta(seconds=3),
            quotes=(quote(),),
        )
        self.assertEqual(restored.snapshot_id, initial.snapshot_id)
        self.assertGreater(restored.checked_at, initial.checked_at)
        restored.refresh(
            effective_date=DAY,
            request_started_at=restored.request_started_at,
            checked_at=restored.checked_at,
            quotes=restored.quotes,
        )
        self.assertEqual(restored.snapshot_id, initial.snapshot_id)

    def test_changed_values_or_date_create_new_snapshot_and_order_does_not(
        self,
    ) -> None:
        initial = book()
        old_id = initial.snapshot_id
        initial.refresh(
            effective_date=DAY,
            request_started_at=NOW + timedelta(seconds=2),
            checked_at=NOW + timedelta(seconds=3),
            quotes=(quote(), quote("EUR", "45")),
        )
        self.assertNotEqual(initial.snapshot_id, old_id)
        old_id = initial.snapshot_id
        initial.refresh(
            effective_date=DAY,
            request_started_at=NOW + timedelta(seconds=4),
            checked_at=NOW + timedelta(seconds=5),
            quotes=tuple(reversed(initial.quotes)),
        )
        self.assertEqual(initial.snapshot_id, old_id)
        initial.refresh(
            effective_date=DAY + timedelta(days=1),
            request_started_at=NOW + timedelta(days=1),
            checked_at=NOW + timedelta(days=1, seconds=1),
            quotes=initial.quotes,
        )
        self.assertNotEqual(initial.snapshot_id, old_id)

    def test_invalid_snapshot_rules_live_in_aggregate(self) -> None:
        cases = [(), (quote(), quote()), (quote("UAH"),)]
        for quotes in cases:
            with (
                self.subTest(quotes=quotes),
                self.assertRaises(InvalidExchangeRateSnapshotError),
            ):
                ExchangeRateBook.create(
                    effective_date=DAY,
                    request_started_at=NOW,
                    checked_at=NOW,
                    quotes=quotes,
                )
        for started, checked, day in (
            (NOW.replace(tzinfo=None), NOW, DAY),
            (NOW, NOW - timedelta(seconds=1), DAY),
            (NOW, NOW, DAY + timedelta(days=1)),
        ):
            with self.assertRaises(InvalidExchangeRateSnapshotError):
                ExchangeRateBook.create(
                    effective_date=day,
                    request_started_at=started,
                    checked_at=checked,
                    quotes=(quote(),),
                )

    def test_late_result_cannot_replace_newer_even_if_it_finished_later(self) -> None:
        initial = book()
        before = (initial.snapshot_id, initial.checked_at, initial.quotes)
        with self.assertRaises(OlderExchangeRateSnapshotError):
            initial.refresh(
                effective_date=DAY,
                request_started_at=NOW - timedelta(seconds=1),
                checked_at=NOW + timedelta(seconds=10),
                quotes=(quote(rate="40"),),
            )
        self.assertEqual(
            before, (initial.snapshot_id, initial.checked_at, initial.quotes)
        )
        with self.assertRaises(OlderExchangeRateSnapshotError):
            initial.refresh(
                effective_date=DAY,
                request_started_at=NOW,
                checked_at=NOW + timedelta(seconds=1),
                quotes=(quote(rate="40"),),
            )


class NbuSourceTests(unittest.IsolatedAsyncioTestCase):
    async def fetch(
        self, content: str, *, status: int = 200, headers: dict[str, str] | None = None
    ) -> SourceExchangeRateSnapshotDTO:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, text=content, headers=headers)
            )
        ) as client:
            return await NbuExchangeRateSource(client, Clock(NOW)).fetch(DAY)

    async def test_exact_decimal_units_date_and_timeout_contract(self) -> None:
        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url).split("?")[0], NBU_URL)
            self.assertEqual(request.url.params["date"], "11.10.2026")
            self.assertIn("json", request.url.params)
            self.assertEqual(request.extensions["timeout"]["read"], 10)
            return httpx.Response(200, text=body(units="100"))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            result = await NbuExchangeRateSource(client, Clock()).fetch(DAY)
        self.assertEqual(result.quotes[0].rate, Decimal("0.411234567890123457"))
        self.assertEqual(result.quotes[0].numeric_code, "840")
        self.assertEqual(result.effective_date, DAY)

    async def test_invalid_responses_are_rejected_as_a_whole(self) -> None:
        duplicate = body()[:-1] + "," + body()[1:]
        invalid = [
            "[]",
            "{}",
            "not-json",
            "[null]",
            duplicate,
            body(day="12.10.2026"),
            body(day="10.10.2026"),
            body(numeric="84"),
            body(code="us"),
            body(amount="0"),
            body(amount="-1"),
            body(amount="NaN"),
            body(amount="Infinity"),
            body(amount="1e100"),
            body(amount="1e-100"),
            body(units="0"),
            body(units="true"),
            body(amount="true"),
            body(units="1.5"),
        ]
        for content in invalid:
            with self.subTest(content=content), self.assertRaises(NbuResponseError):
                await self.fetch(content)

    async def test_http_errors_retry_after_seconds_and_http_date(self) -> None:
        for header, expected in (
            ("120", 120.0),
            ("Sun, 11 Oct 2026 12:01:00 GMT", 60.0),
            ("bad", None),
            ("Sun, 11 Oct 2026 11:00:00 GMT", 0.0),
        ):
            with (
                self.subTest(header=header),
                self.assertRaises(NbuRateLimitError) as caught,
            ):
                await self.fetch(
                    "secret-response", status=429, headers={"Retry-After": header}
                )
            self.assertEqual(caught.exception.retry_after_seconds, expected)
            self.assertNotIn("secret-response", str(caught.exception))
        with self.assertRaises(NbuHttpError) as caught:
            await self.fetch("private", status=503)
        self.assertEqual(caught.exception.status_code, 503)

    async def test_timeout_and_network_error_preserve_cause(self) -> None:
        for error in (httpx.ReadTimeout, httpx.ConnectError):

            def fail(request: httpx.Request) -> httpx.Response:
                raise error("unavailable", request=request)

            async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
                with self.assertRaises(NbuTransportError) as caught:
                    await NbuExchangeRateSource(client, Clock()).fetch(DAY)
                self.assertIsInstance(caught.exception.__cause__, error)


class RefreshHandlerTests(unittest.IsolatedAsyncioTestCase):
    def make_handler(
        self,
        *,
        existing: ExchangeRateBook | None = None,
        quotes: tuple[SourceExchangeRateDTO, ...] | None = None,
        records: tuple[ExchangeRateCurrencyDTO, ...] | None = None,
        clock: Clock | None = None,
    ) -> tuple[RefreshExchangeRatesHandler, list[AsyncMock], list[str]]:
        steps: list[str] = []
        source, catalog, repository, lock = [AsyncMock() for _ in range(4)]

        async def fetch(day: date) -> SourceExchangeRateSnapshotDTO:
            steps.append("source")
            return SourceExchangeRateSnapshotDTO(
                day,
                (
                    quotes
                    if quotes is not None
                    else (SourceExchangeRateDTO("USD", "840", Decimal("41")),)
                ),
            )

        async def active(codes: tuple[str, ...]) -> tuple[ExchangeRateCurrencyDTO, ...]:
            steps.append("catalog")
            return (
                records
                if records is not None
                else (ExchangeRateCurrencyDTO("USD", "840", False),)
            )

        async def acquire() -> None:
            steps.append("lock")

        async def get() -> ExchangeRateBook | None:
            steps.append("get")
            return existing

        async def save(value: ExchangeRateBook) -> None:
            steps.append("save")

        source.fetch.side_effect = fetch
        catalog.get_active.side_effect = active
        repository.get.side_effect = get
        repository.save.side_effect = save
        lock.acquire.side_effect = acquire
        return (
            RefreshExchangeRatesHandler(
                source,
                catalog,
                repository,
                lock,
                clock or Clock(NOW + timedelta(seconds=2), NOW + timedelta(seconds=3)),
            ),
            [source, catalog, repository, lock],
            steps,
        )

    async def test_network_is_first_and_confirmation_keeps_id(self) -> None:
        existing = book()
        handler, mocks, steps = self.make_handler(existing=existing)
        result = await handler.execute(RefreshExchangeRatesCommand())
        self.assertEqual(steps, ["source", "catalog", "lock", "get", "save"])
        self.assertEqual(result.snapshot_id, existing.snapshot_id.uuid)
        self.assertEqual(result.quote_count, 1)
        mocks[0].fetch.assert_awaited_once_with(DAY)

    async def test_unknown_and_metals_are_excluded_with_diagnostics(self) -> None:
        quotes = tuple(
            SourceExchangeRateDTO(code, numeric, Decimal("41"))
            for code, numeric in (("USD", "840"), ("XAU", "959"), ("ZZZ", "999"))
        )
        records = (
            ExchangeRateCurrencyDTO("USD", "840", False),
            ExchangeRateCurrencyDTO("XAU", "959", True),
        )
        handler, _, _ = self.make_handler(quotes=quotes, records=records)
        result = await handler.execute(RefreshExchangeRatesCommand())
        self.assertEqual(
            (
                result.quote_count,
                result.excluded_metal_count,
                result.excluded_unknown_count,
            ),
            (1, 1, 1),
        )

    async def test_empty_filtered_or_numeric_mismatch_never_lock_or_save(self) -> None:
        for records, error in (
            ((), InvalidExchangeRateSnapshotError),
            (
                (ExchangeRateCurrencyDTO("USD", "978", False),),
                ExchangeRateCatalogMismatchError,
            ),
        ):
            handler, mocks, _ = self.make_handler(records=records)
            with self.assertRaises(error):
                await handler.execute(RefreshExchangeRatesCommand())
            mocks[3].acquire.assert_not_awaited()
            mocks[2].save.assert_not_awaited()

    async def test_failure_and_midnight_preserve_book(self) -> None:
        handler, mocks, _ = self.make_handler()
        mocks[0].fetch.side_effect = NbuTransportError("unavailable")
        with self.assertRaises(NbuTransportError):
            await handler.execute(RefreshExchangeRatesCommand())
        mocks[1].get_active.assert_not_awaited()
        mocks[2].save.assert_not_awaited()
        # В октябре Kyiv UTC+3: локальная дата меняется в 21:00 UTC.
        handler, mocks, _ = self.make_handler(
            clock=Clock(
                datetime(2026, 10, 11, 20, 59, 59, tzinfo=UTC),
                datetime(2026, 10, 11, 21, tzinfo=UTC),
            )
        )
        with self.assertRaises(ExchangeRateSourceError):
            await handler.execute(RefreshExchangeRatesCommand())
        mocks[1].get_active.assert_not_awaited()

    async def test_batch_catalog_normalizes_deduplicates_and_classifies(self) -> None:
        repository = AsyncMock()
        repository.get_active_codes.return_value = (
            GetCurrencyValidationCatalogRecordDTO("USD", "840", 2),
            GetCurrencyValidationCatalogRecordDTO("XAU", "959", None),
        )
        handler = GetCurrencyValidationCatalogHandler(repository)
        result = await handler.execute(
            GetCurrencyValidationCatalogQuery((" usd ", "USD", "XAU", "ZZZ"))
        )
        repository.get_active_codes.assert_awaited_once_with(("USD", "XAU", "ZZZ"))
        self.assertEqual(result.missing_codes, ("ZZZ",))
        self.assertTrue(result.currencies[1].is_metal)
        adapted = await ReferenceDataExchangeRateCurrencyCatalog(handler).get_active(
            ("USD",)
        )
        self.assertIsInstance(adapted[0], ExchangeRateCurrencyDTO)

    async def test_cli_registers_refresh_and_prints_only_after_commit_result(
        self,
    ) -> None:
        from src.management.commands.currency import register, handle_refresh

        parser = argparse.ArgumentParser()
        register(parser.add_subparsers())
        args = parser.parse_args(
            [
                "currency",
                "refresh",
                "--tenant-id",
                "00000000-0000-4000-8000-000000000001",
            ]
        )
        self.assertIs(args.handler, handle_refresh)
        handler, _, _ = self.make_handler()
        result = await handler.execute(RefreshExchangeRatesCommand())
        with (
            patch("src.management.commands.currency.db_helper") as db,
            patch(
                "src.management.commands.currency.refresh_exchange_rates",
                new=AsyncMock(return_value=result),
            ) as refresh,
            patch("builtins.print") as output,
        ):
            db.initialize_for_startup = AsyncMock()
            db.dispose = AsyncMock()
            self.assertEqual(await handle_refresh(args), 0)
            refresh.assert_awaited_once()
            self.assertEqual(refresh.call_args.kwargs["tenant_id"], args.tenant_id)
            output.assert_called_once()
            self.assertIn("OK nbu", output.call_args.args[0])
            db.dispose.assert_awaited_once()
