from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.currency.domain.models import (
    RateDerivation,
    RateQuote,
    ConversionPurpose,
)


from src.modules.currency.domain.errors import (
    CurrencyNotFound,
    CurrencyDisabled,
    CurrencyPolicyNotConfigured,
    FunctionalCurrencyNotConfigured,
    ExchangeRateNotFound,
)

# Only expected business failures may become an unavailable offer conversion.
UNAVAILABLE_CONVERSION = (
    CurrencyNotFound,
    CurrencyDisabled,
    CurrencyPolicyNotConfigured,
    FunctionalCurrencyNotConfigured,
    ExchangeRateNotFound,
)


@dataclass(frozen=True, slots=True)
class ConversionSnapshot:
    source_currency: CurrencyCodeVO
    target_currency: CurrencyCodeVO
    rate: Decimal
    requested_date: date
    effective_date: date
    converted_at: datetime
    provider_code: str
    derivation: RateDerivation
    source_rate_ids: tuple[EntityIdVO, ...]
    bridge_currency: CurrencyCodeVO | None = None
    policy_version: int = 1


@dataclass(frozen=True, slots=True)
class ConvertedMoney:
    original: Money
    converted: Money
    conversion: ConversionSnapshot


class CurrencyFacade(Protocol):
    async def get_business_dates(
        self, *, tenant_id: EntityIdVO, timestamps: list[datetime]
    ) -> list[date]: ...
    async def get_business_date(
        self, *, tenant_id: EntityIdVO, timestamp: datetime | None = None
    ) -> date: ...
    async def convert_many(
        self,
        *,
        tenant_id: EntityIdVO,
        items: list[tuple[Money, date]],
        target: CurrencyCodeVO | None = None,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
    ) -> list: ...
    async def get_functional_currency(
        self, *, tenant_id: EntityIdVO, business_date: date
    ) -> CurrencyCodeVO: ...
    async def resolve_rate(
        self,
        *,
        tenant_id: EntityIdVO,
        source: CurrencyCodeVO,
        target: CurrencyCodeVO,
        date: date,
    ) -> RateQuote: ...
    async def convert(
        self,
        *,
        tenant_id: EntityIdVO,
        money: Money,
        target: CurrencyCodeVO,
        date: date,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
    ) -> ConvertedMoney: ...
    async def convert_to_functional(
        self,
        *,
        tenant_id: EntityIdVO,
        money: Money,
        business_date: date,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
    ) -> ConvertedMoney: ...


def conversion_payload(result: ConvertedMoney) -> dict:
    """Portable public contract for a consumer-owned historical record."""
    snapshot = result.conversion
    return {
        "original": {
            "amount": format(result.original.amount, "f"),
            "currency": str(result.original.currency),
        },
        "converted": {
            "amount": format(result.converted.amount, "f"),
            "currency": str(result.converted.currency),
        },
        "conversion": {
            "source_currency": str(snapshot.source_currency),
            "target_currency": str(snapshot.target_currency),
            "rate": format(snapshot.rate, "f"),
            "requested_date": snapshot.requested_date.isoformat(),
            "effective_date": snapshot.effective_date.isoformat(),
            "converted_at": snapshot.converted_at.isoformat(),
            "provider_code": snapshot.provider_code,
            "derivation": snapshot.derivation.value,
            "source_rate_ids": [str(i) for i in snapshot.source_rate_ids],
            "bridge_currency": (
                str(snapshot.bridge_currency) if snapshot.bridge_currency else None
            ),
            "policy_version": snapshot.policy_version,
        },
    }
