from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)
from src.modules.shared.application.time.business_calendar import BusinessCalendar
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.currency.application.provider.dto.provider_status_dto import (
    ProviderStatusDTO,
)
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import unittest

import httpx

from src.config.feature.currency_config import NbuSettings
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.money_errors import (
    InvalidCurrencyCodeError,
    InvalidMoneyError,
    CurrencyMismatchError,
)
from src.modules.currency.domain.directory.entity import CurrencyInfo
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.currency.domain.conversion.quantizer import MoneyQuantizer
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.domain.exchange_rate.error import ExchangeRateNotFound
from src.modules.currency.domain.exchange_rate.error import CrossRateUnavailable
from src.modules.currency.domain.conversion.error import CurrencyPrecisionUndefined
from src.modules.currency.domain.provider.error import ProviderRateInvalid
from src.modules.currency.domain.provider.error import ProviderUnavailable
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyChangeNotAllowed,
)
from src.modules.currency.domain.exchange_rate.service import ExchangeRateResolver
from src.modules.currency.application.conversion.service import MoneyConversionService
from test.currency_support import configuration_cases
from src.modules.currency.application.functional_currency.command.schedule_functional_currency_change_command import (
    ScheduleFunctionalCurrencyChange,
)
from src.modules.currency.infrastructure.providers.nbu.client import NbuClient
from src.modules.currency.infrastructure.providers.nbu.mapper import map_rates
from src.modules.price_lists.application.offer.service.money import OfferMoneyService

USD, EUR, UAH = Code("USD"), Code("EUR"), Code("UAH")
TENANT = EntityIdVO(uuid4())
NOW = datetime(2026, 9, 20, 21, 30, tzinfo=UTC)
DAY = date(2026, 9, 21)
FRIDAY = date(2026, 9, 18)
POLICY = CurrencyPolicy(
    UAH,
    ProviderCode("NBU"),
    RateDatePolicy.PREVIOUS_AVAILABLE,
    RoundingMode.HALF_UP,
    True,
    UAH,
)


class LocalRates:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    async def find(self, *, tenant_id, provider, pair, requested_date, policy):
        self.calls += 1
        valid = [
            r
            for r in self.rows
            if r.pair == pair
            and r.provider_code == provider
            and r.is_current
            and (
                r.effective_date == requested_date
                if policy == RateDatePolicy.EXACT
                else r.effective_date <= requested_date
            )
        ]
        return max(valid, key=lambda r: r.effective_date) if valid else None

    async def find_cross(
        self, *, tenant_id, provider, pair, bridge, requested_date, policy
    ):
        self.calls += 1
        a = [
            r
            for r in self.rows
            if r.pair
            in (CurrencyPair(pair.source, bridge), CurrencyPair(bridge, pair.source))
            and r.provider_code == provider
            and r.is_current
        ]
        b = [
            r
            for r in self.rows
            if r.pair
            in (CurrencyPair(bridge, pair.target), CurrencyPair(pair.target, bridge))
            and r.provider_code == provider
            and r.is_current
        ]
        pairs = [
            (x, y)
            for x in a
            for y in b
            if x.effective_date == y.effective_date
            and (
                x.effective_date == requested_date
                if policy == RateDatePolicy.EXACT
                else x.effective_date <= requested_date
            )
        ]
        return max(pairs, key=lambda p: p[0].effective_date) if pairs else None


def rate(source, target, value, day=FRIDAY, provider="NBU"):
    return RateRecord(
        EntityIdVO(uuid4()),
        CurrencyPair(source, target),
        Decimal(value),
        day,
        ProviderCode(provider),
    )


def services(rows=(), policy=POLICY):
    directory = SimpleNamespace(
        get=AsyncMock(side_effect=lambda c: CurrencyInfo(c, str(c), 2)),
        list_active=AsyncMock(
            return_value=[CurrencyInfo(c, str(c), 2) for c in (USD, EUR, UAH)]
        ),
    )
    policies = SimpleNamespace(
        get=AsyncMock(return_value=policy),
        enabled=AsyncMock(return_value={USD, EUR, UAH}),
        lock=AsyncMock(),
    )
    period = FunctionalCurrencyPeriod(
        EntityIdVO(uuid4()), UAH, date(2020, 1, 1), None, NOW, TENANT, "Initial"
    )
    periods = SimpleNamespace(
        list_periods=AsyncMock(return_value=[period]),
        get_for_date=AsyncMock(return_value=period),
        add=AsyncMock(),
        close=AsyncMock(),
    )
    rates = LocalRates(list(rows))
    resolver = ExchangeRateResolver(rates, policies, directory, policies)
    from src.modules.currency.application.policy.dto.currency_policy_dto import (
        CurrencyPolicyDTO,
    )

    async def read_settings(*, tenant_id):
        return CurrencyPolicyDTO.from_entity(await policies.get(tenant_id=tenant_id))

    settings = SimpleNamespace(get=read_settings)
    facade = MoneyConversionService(
        directory,
        policies,
        periods,
        resolver,
        SimpleNamespace(now=lambda: NOW),
        settings,
        AsyncMock(),
        TENANT,
        policies,
    )
    return SimpleNamespace(
        directory=directory,
        policies=policies,
        periods=periods,
        rates=rates,
        resolver=resolver,
        facade=facade,
        clock=SimpleNamespace(now=lambda: NOW),
    )


class MoneyTests(unittest.TestCase):
    def test_open_codes_and_ascii_validation(self):
        self.assertEqual(Code(" jpy "), Code("JPY"))
        for bad in ("US", "USDD", "U1D", "uſd", "１２３", None, 100):
            with self.subTest(bad=bad), self.assertRaises(InvalidCurrencyCodeError):
                Code(bad)

    def test_money_arithmetic_without_quantization(self):
        money = Money(Decimal("1.234567"), USD)
        self.assertEqual((money * 100).amount, Decimal("123.456700"))
        self.assertEqual((money + money - money).amount, money.amount)
        self.assertEqual((money / 2).amount, Decimal("0.6172835"))
        self.assertTrue(money.is_positive())
        self.assertTrue(Money(0, USD).is_zero())
        with self.assertRaises(FrozenInstanceError):
            money.amount = Decimal(2)
        with self.assertRaises(CurrencyMismatchError):
            money + Money(1, EUR)
        for bad in (0.1, True, Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(bad=bad), self.assertRaises(InvalidMoneyError):
                Money(bad, USD)
            with self.assertRaises(InvalidMoneyError):
                money * bad
        with self.assertRaises(InvalidMoneyError):
            money / 0

    def test_quantizer_is_an_explicit_boundary(self):
        money = Money(Decimal("1.005"), USD)
        quantizer = MoneyQuantizer()
        self.assertEqual(
            quantizer.quantize(
                money,
                minor_units=2,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.BOOKING,
            ).amount,
            Decimal("1.01"),
        )
        self.assertEqual(
            quantizer.quantize(
                money,
                minor_units=2,
                rounding_mode=RoundingMode.HALF_EVEN,
                purpose=ConversionPurpose.BOOKING,
            ).amount,
            Decimal("1.00"),
        )
        self.assertIs(
            quantizer.quantize(
                money,
                minor_units=None,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.CALCULATION,
            ),
            money,
        )
        with self.assertRaises(CurrencyPrecisionUndefined):
            quantizer.quantize(
                money,
                minor_units=None,
                rounding_mode=RoundingMode.HALF_UP,
                purpose=ConversionPurpose.BOOKING,
            )

    def test_exact_arithmetic_does_not_inherit_small_decimal_precision(self):
        with localcontext() as context:
            context.prec = 3
            money = Money(Decimal("123456789.123456789"), USD)
            self.assertEqual(
                (money + Money(Decimal("0.000000001"), USD)).amount,
                Decimal("123456789.123456790"),
            )
            self.assertEqual((money * 100).amount, Decimal("12345678912.345678900"))
            self.assertEqual(
                (money - Money(Decimal("0.000000001"), USD)).amount,
                Decimal("123456789.123456788"),
            )


class CurrencyConversionTests(unittest.IsolatedAsyncioTestCase):
    async def test_direct_previous_and_immutable_snapshot(self):
        data = services([rate(USD, UAH, "41.25")])
        first = await data.facade.convert_to_functional(
            tenant_id=TENANT, money=Money(100, USD), business_date=DAY
        )
        self.assertEqual(first.converted.amount, Decimal("4125"))
        self.assertEqual(first.conversion.requested_date, DAY)
        self.assertEqual(first.conversion.effective_date, FRIDAY)
        data.rates.rows = [rate(USD, UAH, "42.10")]
        second = await data.facade.convert_to_functional(
            tenant_id=TENANT, money=Money(100, USD), business_date=DAY
        )
        self.assertEqual(first.converted.amount, Decimal("4125"))
        self.assertEqual(second.converted.amount, Decimal("4210"))

    async def test_inverse_identity_and_exact_missing(self):
        data = services([rate(USD, UAH, "40")])
        inverse = await data.facade.convert(
            tenant_id=TENANT, money=Money(100, UAH), target=USD, date=DAY
        )
        self.assertEqual(inverse.converted.amount, Decimal("2.5"))
        self.assertEqual(inverse.conversion.derivation, "inverse")
        identity = await data.facade.convert(
            tenant_id=TENANT, money=Money(100, UAH), target=UAH, date=DAY
        )
        self.assertEqual(identity.conversion.rate, 1)
        self.assertEqual(identity.conversion.provider_code, "INTERNAL")
        data.policies.get.return_value = replace(
            POLICY, rate_date_policy=RateDatePolicy.EXACT
        )
        with self.assertRaises(ExchangeRateNotFound):
            await data.facade.convert(
                tenant_id=TENANT, money=Money(100, USD), target=UAH, date=DAY
            )

    async def test_cross_uses_latest_common_date(self):
        data = services(
            [rate(USD, UAH, "40"), rate(EUR, UAH, "50"), rate(USD, UAH, "42", DAY)]
        )
        result = await data.facade.convert(
            tenant_id=TENANT, money=Money(100, USD), target=EUR, date=DAY
        )
        self.assertEqual(result.converted.amount, 80)
        self.assertEqual(result.conversion.effective_date, FRIDAY)
        self.assertEqual(len(result.conversion.source_rate_ids), 2)
        data.rates.rows = [rate(USD, UAH, "40", DAY), rate(EUR, UAH, "50", FRIDAY)]
        with self.assertRaises(CrossRateUnavailable):
            await data.facade.convert(
                tenant_id=TENANT, money=Money(100, USD), target=EUR, date=DAY
            )

    async def test_never_uses_future_or_another_provider(self):
        data = services(
            [
                rate(USD, UAH, "40", date(2026, 9, 22)),
                rate(USD, UAH, "39", FRIDAY, "MANUAL"),
            ]
        )
        with self.assertRaises(ExchangeRateNotFound):
            await data.facade.convert(
                tenant_id=TENANT, money=Money(100, USD), target=UAH, date=DAY
            )

    async def test_disabled_identity_and_unconfigured_are_not_shortcuts(self):
        data = services()
        data.policies.enabled.return_value = {UAH}
        with self.assertRaises(CurrencyDisabled):
            await data.facade.convert(
                tenant_id=TENANT, money=Money(100, USD), target=USD, date=DAY
            )
        data.policies.get.side_effect = CurrencyPolicyNotConfigured("Missing")
        with self.assertRaises(CurrencyPolicyNotConfigured):
            await data.facade.convert(
                tenant_id=TENANT, money=Money(100, UAH), target=UAH, date=DAY
            )

    async def test_batch_quotes_and_local_business_date(self):
        data = services([rate(USD, UAH, "40")])
        self.assertEqual(BusinessCalendar.date_at(NOW, POLICY.business_timezone), DAY)
        result = await data.facade.convert_many(
            tenant_id=TENANT,
            items=[ConversionRequest(Money(i, USD), DAY) for i in range(1000)],
        )
        self.assertEqual(len(result), 1000)
        self.assertEqual(data.rates.calls, 1)

    async def test_future_change_checked_in_business_timezone(self):
        data = services()
        service = configuration_cases(
            data.directory,
            data.policies,
            data.periods,
            data.rates,
            SimpleNamespace(add=AsyncMock()),
            SimpleNamespace(now=lambda: NOW),
        )
        with self.assertRaises(FunctionalCurrencyChangeNotAllowed):
            await service.schedule(
                ScheduleFunctionalCurrencyChange(
                    TENANT,
                    TENANT,
                    EUR,
                    DAY,
                    "Change",
                    id=FunctionalCurrencyPeriodIdVO(uuid4()),
                )
            )
        period = await service.schedule(
            ScheduleFunctionalCurrencyChange(
                TENANT,
                TENANT,
                EUR,
                date(2026, 9, 22),
                "Change",
                id=FunctionalCurrencyPeriodIdVO(uuid4()),
            )
        )
        self.assertEqual(period.valid_from, date(2026, 9, 22))
        self.assertEqual(data.periods.close.call_args.kwargs["valid_to"], DAY)


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_retry_and_decimal_json(self):
        attempts = []

        def transport(request):
            attempts.append(request)
            if len(attempts) == 1:
                return httpx.Response(503)
            return httpx.Response(
                200,
                text='[{"cc":"USD","rate_per_unit":41.1234567890123456789,"units":1,"exchangedate":"21.09.2026","calcdate":"18.09.2026"}]',
            )

        client = NbuClient(
            NbuSettings(retry_count=1), transport=httpx.MockTransport(transport)
        )
        payload = await client.fetch(start_date=DAY, end_date=DAY)
        rows = map_rates(payload, start_date=DAY, end_date=DAY)
        self.assertEqual(rows[0].rate, Decimal("41.1234567890123456789"))
        self.assertEqual(rows[0].effective_date, DAY)
        self.assertEqual(rows[0].calculated_date, FRIDAY)
        self.assertEqual(len(attempts), 2)

    async def test_mapper_units_and_invalid_batch(self):
        row = dict(cc="JPY", rate="28.125", units=100, exchangedate="21.09.2026")
        result = map_rates([row], start_date=DAY, end_date=DAY)
        self.assertEqual(result[0].rate, Decimal("0.28125"))
        for bad in (
            {**row, "units": 0},
            {**row, "rate": "NaN"},
            {**row, "exchangedate": "22.09.2026"},
        ):
            with self.assertRaises(ProviderRateInvalid):
                map_rates([row, bad], start_date=DAY, end_date=DAY)

    async def test_non_retryable_http_and_bad_json(self):
        for response, error in (
            (httpx.Response(404), ProviderUnavailable),
            (httpx.Response(200, text="broken"), ProviderRateInvalid),
        ):
            client = NbuClient(
                NbuSettings(retry_count=0),
                transport=httpx.MockTransport(lambda _: response),
            )
            with self.assertRaises(error):
                await client.fetch(start_date=DAY, end_date=DAY)


class OfferMoneyTests(unittest.IsolatedAsyncioTestCase):
    def state(self):
        return SimpleNamespace(
            id=EntityIdVO(uuid4()),
            observed_at=NOW,
            purchase_price=Decimal(10),
            rrp=Decimal(15),
            currency="USD",
        )

    async def test_snapshots_are_owned_and_dated_by_offer(self):
        data = services([rate(USD, UAH, "40")])
        snapshots = SimpleNamespace(add_many=AsyncMock())
        service = OfferMoneyService(
            data.facade,
            snapshots,
            data.policies,
            data.clock,
            failures=data.facade.failures,
            operation_id=TENANT,
        )
        await service.capture(TENANT, [self.state()], operation_id=TENANT)
        record = snapshots.add_many.call_args.kwargs["records"][0]
        self.assertEqual(record.conversion.business_date, DAY)
        self.assertEqual(
            record.conversion.purchase_price.converted.amount, Decimal("400")
        )
        self.assertEqual(record.conversion.rrp.converted.amount, Decimal("600"))
        self.assertEqual(data.rates.calls, 1)

    async def test_expected_unavailability_does_not_mask_storage_failure(self):
        data = services()
        snapshots = SimpleNamespace(add_many=AsyncMock())
        service = OfferMoneyService(
            data.facade,
            snapshots,
            data.policies,
            data.clock,
            failures=data.facade.failures,
            operation_id=TENANT,
        )
        await service.capture(TENANT, [self.state()], operation_id=TENANT)
        record = snapshots.add_many.call_args.kwargs["records"][0]
        self.assertEqual(record.conversion.status, "unavailable")
        data.policies.get.side_effect = OSError("database unavailable")
        with self.assertRaises(OSError):
            await service.capture(TENANT, [self.state()], operation_id=TENANT)


class CurrencyManagementTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_range_and_disabled_schedule(self):
        from src.management.cli import build_parser
        from src.modules.currency.presentation.management import sync_rates

        parser = build_parser()
        args = parser.parse_args(
            [
                "currency",
                "sync-rates",
                "--date-from",
                "2026-09-01",
                "--date-to",
                "2026-09-21",
                "--scheduled",
            ]
        )
        self.assertEqual(args.date_from, date(2026, 9, 1))
        self.assertEqual(args.date_to, DAY)
        from unittest.mock import patch

        with patch(
            "src.modules.currency.presentation.management.sync_rates.dnk_config",
            SimpleNamespace(
                CURRENCY=SimpleNamespace(nbu=NbuSettings(sync_enabled=False))
            ),
        ):
            self.assertEqual(await sync_rates(args), 0)

    async def test_disabling_unknown_currency_is_rejected_before_storage(self):
        from src.modules.currency.application.enabled_currency.command.set_enabled_currency_command import (
            SetEnabledCurrency,
        )
        from src.modules.currency.domain.directory.error import CurrencyNotFound

        data = services()
        data.directory.get.side_effect = CurrencyNotFound("Unknown code")
        data.policies.set_enabled = AsyncMock()
        service = configuration_cases(
            data.directory,
            data.policies,
            data.periods,
            data.rates,
            SimpleNamespace(add=AsyncMock()),
            SimpleNamespace(now=lambda: NOW),
        )
        with self.assertRaises(CurrencyNotFound):
            await service.set_enabled(
                SetEnabledCurrency(TENANT, TENANT, Code("QQQ"), False)
            )
        data.policies.set_enabled.assert_not_called()

    async def test_settings_default_is_only_a_read_model(self):
        from src.modules.currency.application.settings.use_case.get_currency_settings import (
            GetCurrencySettingsUseCase,
        )
        from src.modules.currency.application.settings.query.get_currency_settings_query import (
            GetCurrencySettingsQuery,
        )

        data = services()
        data.policies.get.side_effect = CurrencyPolicyNotConfigured("Missing")
        data.policies.enabled.return_value = set()
        data.periods.list_periods.return_value = []
        data.rates.provider_status = AsyncMock(
            return_value=ProviderStatusDTO(None, None)
        )
        result = await GetCurrencySettingsUseCase(
            data.policies,
            data.periods,
            data.rates,
            SimpleNamespace(now=lambda: NOW),
            data.policies,
        )(GetCurrencySettingsQuery(TENANT))
        self.assertFalse(result.configured)
        self.assertIsNone(result.policy)
        self.assertEqual(result.enabled_currencies, ())
        self.assertEqual(result.business_date, DAY)
        data.policies.lock.assert_not_called()
