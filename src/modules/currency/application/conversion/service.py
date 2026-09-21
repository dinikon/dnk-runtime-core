from __future__ import annotations
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from collections.abc import Sequence
from datetime import date
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.currency.application.conversion.dto.conversion_snapshot import (
    ConversionSnapshot,
)
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)
from src.modules.currency.application.conversion.dto.rate_quote_dto import RateQuoteDTO
from src.modules.currency.application.conversion.dto.unavailable_conversion import (
    UnavailableConversion,
)
from src.modules.currency.application.conversion.error import UNAVAILABLE_CONVERSION
from src.modules.currency.application.resolution_failure.command.record_failure import (
    RecordRateResolutionFailure,
)
from src.modules.currency.application.resolution_failure.ports import (
    ResolutionFailureRecorder,
)
from src.modules.currency.application.settings.reader import CurrencySettingsReader
from src.modules.currency.domain.conversion.calculator import ConversionCalculator
from src.modules.currency.domain.conversion.quantizer import MoneyQuantizer
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.exchange_rate.service import ExchangeRateResolver
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyNotConfigured,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import Money


class MoneyConversionService:
    """Convert using dated local quotes and one operation's policy snapshot."""

    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        periods: FunctionalCurrencyRepository,
        resolver: ExchangeRateResolver,
        clock: ClockPort,
        settings: CurrencySettingsReader,
        failures: ResolutionFailureRecorder,
        operation_id: EntityIdVO,
        enabled_currencies: EnabledCurrencyRepository,
    ):
        self.directory, self.policies, self.periods = directory, policies, periods
        self.resolver, self.clock, self.settings = resolver, clock, settings
        self.failures, self.operation_id = failures, operation_id
        self.enabled_currencies = enabled_currencies

    async def get_functional_currency(
        self, *, tenant_id: EntityIdVO, business_date: date
    ) -> CurrencyCodeVO:
        return (
            await self.periods.get_for_date(
                tenant_id=tenant_id, business_date=business_date
            )
        ).currency

    async def resolve_rate(
        self,
        *,
        tenant_id: EntityIdVO,
        source: CurrencyCodeVO,
        target: CurrencyCodeVO,
        date: date,
    ) -> RateQuoteDTO:
        policy = None
        try:
            policy = (await self.settings.get(tenant_id=tenant_id)).to_entity()
            quote = await self.resolver.resolve(
                tenant_id=tenant_id,
                pair=CurrencyPair(source, target),
                requested_date=date,
                policy=policy,
            )
        except UNAVAILABLE_CONVERSION as exc:
            await self._record_failure(
                tenant_id, source, target, date, policy, exc.code
            )
            raise
        return RateQuoteDTO(
            quote.pair,
            quote.rate,
            quote.requested_date,
            quote.effective_date,
            quote.provider_code,
            quote.derivation,
            quote.source_rate_ids,
            quote.bridge_currency,
        )

    async def convert(
        self,
        *,
        tenant_id: EntityIdVO,
        money: Money,
        target: CurrencyCodeVO,
        date: date,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
        precision: int | None = None,
    ) -> ConvertedMoney:
        result = (
            await self.convert_many(
                tenant_id=tenant_id,
                items=[ConversionRequest(money, date, target, purpose, precision)],
            )
        )[0]
        if isinstance(result, UnavailableConversion):
            result.raise_error()
        return result

    async def convert_to_functional(
        self,
        *,
        tenant_id: EntityIdVO,
        money: Money,
        business_date: date,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
        precision: int | None = None,
    ) -> ConvertedMoney:
        result = (
            await self.convert_many(
                tenant_id=tenant_id,
                items=[
                    ConversionRequest(money, business_date, None, purpose, precision)
                ],
            )
        )[0]
        if isinstance(result, UnavailableConversion):
            result.raise_error()
        return result

    async def convert_many(
        self,
        *,
        tenant_id: EntityIdVO,
        items: Sequence[ConversionRequest],
        operation_id: EntityIdVO | None = None,
    ) -> list[ConvertedMoney | UnavailableConversion]:
        """Resolve each distinct pair/date only once for this batch."""
        if not items:
            return []
        policy = None
        try:
            policy = (await self.settings.get(tenant_id=tenant_id)).to_entity()
        except CurrencyPolicyNotConfigured as exc:
            for source, target, day in {
                (i.money.currency, i.target, i.business_date) for i in items
            }:
                await self._record_failure(
                    tenant_id, source, target, day, None, exc.code, operation_id
                )
            return [
                UnavailableConversion(exc.code, str(exc), i.business_date)
                for i in items
            ]
        enabled = await self.enabled_currencies.enabled(tenant_id=tenant_id)
        directory = {i.code: i for i in await self.directory.list_active()}
        periods = (
            await self.periods.list_periods(tenant_id=tenant_id)
            if any(i.target is None for i in items)
            else []
        )
        quotes = {}
        converted_at = self.clock.now()
        results: list[ConvertedMoney | UnavailableConversion] = []
        for item in items:
            money, day = item.money, item.business_date
            target = item.target or next(
                (p.currency for p in periods if p.contains(day)), None
            )
            key = (money.currency, target, day)
            if key not in quotes:
                try:
                    if target is None:
                        raise FunctionalCurrencyNotConfigured(
                            f"No functional currency on {day}."
                        )
                    quotes[key] = await self.resolver.resolve(
                        tenant_id=tenant_id,
                        pair=CurrencyPair(money.currency, target),
                        requested_date=day,
                        policy=policy,
                        enabled=enabled,
                        directory=directory,
                    )
                except UNAVAILABLE_CONVERSION as exc:
                    quotes[key] = UnavailableConversion(exc.code, str(exc), day)
                    await self._record_failure(
                        tenant_id,
                        money.currency,
                        target,
                        day,
                        policy,
                        exc.code,
                        operation_id,
                    )
            quote = quotes[key]
            if isinstance(quote, UnavailableConversion):
                results.append(quote)
                continue
            minor_units = directory[target].minor_units
            converted = MoneyQuantizer().quantize(
                ConversionCalculator().convert(money, quote),
                minor_units=minor_units,
                rounding_mode=policy.rounding_mode,
                purpose=item.purpose,
                precision=item.precision,
            )
            results.append(
                ConvertedMoney(
                    money,
                    converted,
                    ConversionSnapshot(
                        money.currency,
                        target,
                        quote.rate,
                        day,
                        quote.effective_date,
                        converted_at,
                        str(quote.provider_code),
                        quote.derivation,
                        quote.source_rate_ids,
                        quote.bridge_currency,
                        policy.version,
                        item.purpose.value,
                        (
                            item.precision
                            if item.precision is not None
                            else (
                                minor_units
                                if item.purpose != ConversionPurpose.CALCULATION
                                else None
                            )
                        ),
                        policy.rounding_mode.value,
                        38 if quote.derivation.value in ("inverse", "cross") else None,
                        minor_units,
                    ),
                )
            )
        return results

    async def _record_failure(
        self,
        tenant_id: EntityIdVO,
        source: CurrencyCodeVO,
        target: CurrencyCodeVO | None,
        day: date,
        policy: CurrencyPolicy | None,
        code: str,
        operation_id: EntityIdVO | None = None,
    ) -> None:
        await self.failures(
            RecordRateResolutionFailure(
                tenant_id,
                operation_id or self.operation_id,
                source,
                target,
                day,
                policy.provider_code if policy else None,
                policy.version if policy else 0,
                code,
            )
        )


__all__ = ["MoneyConversionService"]
