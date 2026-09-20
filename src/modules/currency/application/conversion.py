from datetime import date
from decimal import Decimal, localcontext

from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.money import Money
from src.modules.currency.domain.models import (
    CurrencyPair,
    ProviderCode,
    RateDerivation,
    RateQuote,
    RateDatePolicy,
    ConversionCalculator,
    MoneyQuantizer,
    ConversionPurpose,
)
from src.modules.currency.domain.errors import (
    CurrencyNotFound,
    CurrencyDisabled,
    CurrencyPolicyNotConfigured,
    FunctionalCurrencyNotConfigured,
    ExchangeRateNotFound,
    CrossRateUnavailable,
)
from .contracts import ConversionSnapshot, ConvertedMoney, UNAVAILABLE_CONVERSION


class ExchangeRateResolver:
    """Resolves locally stored quotes; never owns a provider HTTP adapter."""

    def __init__(self, rates, policies, directory):
        self.rates, self.policies, self.directory = rates, policies, directory

    async def resolve(
        self,
        *,
        tenant_id,
        pair,
        requested_date,
        policy=None,
        enabled=None,
        directory=None,
    ):
        policy = policy or await self.policies.get(tenant_id=tenant_id)
        if enabled is None:
            enabled = await self.policies.enabled(tenant_id=tenant_id)
        for code in {pair.source, pair.target}:
            info = (
                directory.get(code)
                if directory is not None
                else await self.directory.get(code)
            )
            if info is None or not info.is_active:
                raise CurrencyNotFound(f"Currency {code} is not active.")
            if code not in enabled:
                raise CurrencyDisabled(f"Currency {code} is not enabled.")
        if pair.source == pair.target:
            return RateQuote(
                pair,
                Decimal(1),
                requested_date,
                requested_date,
                ProviderCode("INTERNAL"),
                RateDerivation.IDENTITY,
            )
        args = dict(
            tenant_id=tenant_id,
            provider=policy.provider_code,
            requested_date=requested_date,
            policy=policy.rate_date_policy,
        )
        direct = await self.rates.find(pair=pair, **args)
        if direct is not None:
            return RateQuote(
                pair,
                direct.rate,
                requested_date,
                direct.effective_date,
                policy.provider_code,
                RateDerivation.DIRECT,
                (direct.id,),
            )
        inverse = await self.rates.find(pair=pair.inverse(), **args)
        if inverse is not None:
            with localcontext() as context:
                context.prec = 38
                return RateQuote(
                    pair,
                    Decimal(1) / inverse.rate,
                    requested_date,
                    inverse.effective_date,
                    policy.provider_code,
                    RateDerivation.INVERSE,
                    (inverse.id,),
                )
        if policy.allow_cross_rate and policy.bridge_currency not in (
            pair.source,
            pair.target,
        ):
            legs = await self.rates.find_cross(
                pair=pair, bridge=policy.bridge_currency, **args
            )
            if legs is not None:
                first, second = legs
                if first.effective_date != second.effective_date:
                    raise CrossRateUnavailable(
                        "Cross-rate legs must use the same effective date."
                    )
                with localcontext() as context:
                    context.prec = max(
                        38,
                        len(first.rate.as_tuple().digits)
                        + len(second.rate.as_tuple().digits),
                    )
                    numerator = (
                        first.rate if first.pair.source == pair.source else Decimal(1)
                    ) * (
                        second.rate
                        if second.pair.source == policy.bridge_currency
                        else Decimal(1)
                    )
                    denominator = (
                        Decimal(1) if first.pair.source == pair.source else first.rate
                    ) * (
                        Decimal(1)
                        if second.pair.source == policy.bridge_currency
                        else second.rate
                    )
                    context.prec = 38
                    return RateQuote(
                        pair,
                        numerator / denominator,
                        requested_date,
                        first.effective_date,
                        policy.provider_code,
                        RateDerivation.CROSS,
                        (first.id, second.id),
                        policy.bridge_currency,
                    )
            raise CrossRateUnavailable(
                f"No common-date cross rate for {pair.source}/{pair.target} on {requested_date}."
            )
        raise ExchangeRateNotFound(
            f"No {policy.provider_code} rate for {pair.source}/{pair.target} on {requested_date}."
        )


class MoneyConversionService:
    """CurrencyFacade implementation, with operation-local batch de-duplication."""

    def __init__(self, directory, policies, periods, resolver, clock: ClockPort):
        self.directory, self.policies, self.periods = directory, policies, periods
        self.resolver, self.clock = resolver, clock

    async def get_business_date(self, *, tenant_id, timestamp=None):
        from zoneinfo import ZoneInfo

        policy = await self.policies.get(tenant_id=tenant_id)
        return (
            (timestamp or self.clock.now())
            .astimezone(ZoneInfo(policy.business_timezone))
            .date()
        )

    async def get_business_dates(self, *, tenant_id, timestamps):
        from zoneinfo import ZoneInfo

        policy = await self.policies.get(tenant_id=tenant_id)
        zone = ZoneInfo(policy.business_timezone)
        return [stamp.astimezone(zone).date() for stamp in timestamps]

    async def get_functional_currency(self, *, tenant_id, business_date):
        return (
            await self.periods.get_for_date(
                tenant_id=tenant_id, business_date=business_date
            )
        ).currency

    async def resolve_rate(self, *, tenant_id, source, target, date):
        return await self.resolver.resolve(
            tenant_id=tenant_id, pair=CurrencyPair(source, target), requested_date=date
        )

    async def convert(
        self, *, tenant_id, money, target, date, purpose=ConversionPurpose.CALCULATION
    ):
        result = (
            await self.convert_many(
                tenant_id=tenant_id,
                items=[(money, date)],
                target=target,
                purpose=purpose,
            )
        )[0]
        if isinstance(result, Exception):
            raise result
        return result

    async def convert_to_functional(
        self, *, tenant_id, money, business_date, purpose=ConversionPurpose.CALCULATION
    ):
        result = (
            await self.convert_many(
                tenant_id=tenant_id, items=[(money, business_date)], purpose=purpose
            )
        )[0]
        if isinstance(result, Exception):
            raise result
        return result

    async def convert_many(
        self, *, tenant_id, items, target=None, purpose=ConversionPurpose.CALCULATION
    ):
        """Resolve once per distinct pair/date, not once per monetary value."""
        if not items:
            return []
        try:
            policy = await self.policies.get(tenant_id=tenant_id)
        except CurrencyPolicyNotConfigured as exc:
            return [exc for _ in items]
        enabled = await self.policies.enabled(tenant_id=tenant_id)
        directory = {info.code: info for info in await self.directory.list_active()}
        periods = (
            await self.periods.list_periods(tenant_id=tenant_id)
            if target is None
            else []
        )
        quotes = {}
        converted_at = self.clock.now()
        results = []
        for money, day in items:
            try:
                currency = target or next(
                    (p.currency for p in periods if p.contains(day)), None
                )
                if currency is None:
                    raise FunctionalCurrencyNotConfigured(
                        f"No functional currency on {day}."
                    )
                key = (money.currency, currency, day)
                if key not in quotes:
                    try:
                        quotes[key] = await self.resolver.resolve(
                            tenant_id=tenant_id,
                            pair=CurrencyPair(money.currency, currency),
                            requested_date=day,
                            policy=policy,
                            enabled=enabled,
                            directory=directory,
                        )
                    except UNAVAILABLE_CONVERSION as exc:
                        quotes[key] = exc
                quote = quotes[key]
                if isinstance(quote, Exception):
                    raise quote
                result = ConversionCalculator().convert(money, quote)
                result = MoneyQuantizer().quantize(
                    result,
                    minor_units=directory[currency].minor_units,
                    rounding_mode=policy.rounding_mode,
                    purpose=purpose,
                )
                results.append(
                    ConvertedMoney(
                        money,
                        result,
                        ConversionSnapshot(
                            money.currency,
                            currency,
                            quote.rate,
                            day,
                            quote.effective_date,
                            converted_at,
                            str(quote.provider_code),
                            quote.derivation,
                            quote.source_rate_ids,
                            quote.bridge_currency,
                            policy.version,
                        ),
                    )
                )
            except UNAVAILABLE_CONVERSION as exc:
                results.append(exc)
        return results
