from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, localcontext
from enum import StrEnum
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.money import Money
from .errors import (
    CurrencyError,
    InvalidExchangeRate,
    CurrencyPrecisionUndefined,
    FunctionalCurrencyChangeNotAllowed,
)


class RateDatePolicy(StrEnum):
    EXACT = "exact"
    PREVIOUS_AVAILABLE = "previous_available"


class RateDerivation(StrEnum):
    DIRECT = "direct"
    INVERSE = "inverse"
    CROSS = "cross"
    IDENTITY = "identity"


class RoundingMode(StrEnum):
    HALF_UP = "ROUND_HALF_UP"
    HALF_EVEN = "ROUND_HALF_EVEN"
    DOWN = "ROUND_DOWN"
    UP = "ROUND_UP"


class ConversionPurpose(StrEnum):
    CALCULATION = "calculation"
    BOOKING = "booking"
    DISPLAY = "display"


@dataclass(frozen=True, slots=True)
class ProviderCode:
    value: str

    def __post_init__(self):
        import re

        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]{0,31}", self.value
        ):
            raise CurrencyError("Invalid provider code.")
        object.__setattr__(self, "value", self.value.upper())

    def __str__(self):
        return self.value


@dataclass(frozen=True, slots=True)
class CurrencyInfo:
    code: CurrencyCodeVO
    name: str
    minor_units: int | None
    numeric_code: str | None = None
    symbol: str | None = None
    is_active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True, slots=True)
class CurrencyPair:
    source: CurrencyCodeVO
    target: CurrencyCodeVO

    def inverse(self):
        return CurrencyPair(self.target, self.source)


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    pair: CurrencyPair
    value: Decimal

    def __post_init__(self):
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value <= 0
        ):
            raise InvalidExchangeRate("Rate must be a positive finite Decimal.")


@dataclass(frozen=True, slots=True)
class RateRecord:
    id: EntityIdVO
    pair: CurrencyPair
    rate: Decimal
    effective_date: date
    provider_code: ProviderCode
    revision: int = 1
    is_current: bool = True
    calculated_date: date | None = None

    def __post_init__(self):
        ExchangeRate(self.pair, self.rate)


@dataclass(frozen=True, slots=True)
class RateQuote:
    pair: CurrencyPair
    rate: Decimal
    requested_date: date
    effective_date: date
    provider_code: ProviderCode
    derivation: RateDerivation
    source_rate_ids: tuple[EntityIdVO, ...] = ()
    bridge_currency: CurrencyCodeVO | None = None

    def __post_init__(self):
        ExchangeRate(self.pair, self.rate)
        if self.effective_date > self.requested_date:
            raise InvalidExchangeRate("A quote cannot use a future rate.")


@dataclass(frozen=True, slots=True)
class CurrencyPolicy:
    default_transaction_currency: CurrencyCodeVO
    provider_code: ProviderCode
    rate_date_policy: RateDatePolicy
    rounding_mode: RoundingMode
    allow_cross_rate: bool
    bridge_currency: CurrencyCodeVO
    business_timezone: str = "Europe/Kyiv"
    version: int = 1

    def __post_init__(self):
        try:
            ZoneInfo(self.business_timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise CurrencyError("Unknown business timezone.") from None
        if self.version < 1:
            raise CurrencyError("Policy version must be positive.")


@dataclass(frozen=True, slots=True)
class FunctionalCurrencyPeriod:
    id: EntityIdVO
    currency: CurrencyCodeVO
    valid_from: date
    valid_to: date | None
    created_at: datetime
    created_by: EntityIdVO
    reason: str

    def __post_init__(self):
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise CurrencyError("Period end precedes its start.")
        if not self.reason.strip():
            raise CurrencyError("A reason is required.")

    def contains(self, day: date) -> bool:
        return self.valid_from <= day and (
            self.valid_to is None or day <= self.valid_to
        )

    def overlaps(self, other: FunctionalCurrencyPeriod) -> bool:
        return self.valid_from <= (other.valid_to or date.max) and other.valid_from <= (
            self.valid_to or date.max
        )

    def validate_successor(
        self, other: FunctionalCurrencyPeriod, business_date: date
    ) -> None:
        if self.valid_to is not None or other.valid_from <= max(
            self.valid_from, business_date
        ):
            raise FunctionalCurrencyChangeNotAllowed(
                "Append a future period after the last open period."
            )
        if self.currency == other.currency:
            raise FunctionalCurrencyChangeNotAllowed(
                "The new currency equals the last scheduled currency."
            )


class ConversionCalculator:
    def convert(self, money: Money, quote: RateQuote) -> Money:
        if money.currency != quote.pair.source:
            from src.modules.shared.domain.value_object.money_errors import (
                CurrencyMismatchError,
            )

            raise CurrencyMismatchError("Money does not match quote source.")
        with localcontext() as context:
            context.prec = max(
                38,
                len(money.amount.as_tuple().digits) + len(quote.rate.as_tuple().digits),
            )
            return Money(money.amount * quote.rate, quote.pair.target)


class MoneyQuantizer:
    def quantize(
        self,
        money: Money,
        *,
        minor_units: int | None,
        rounding_mode: RoundingMode,
        purpose: ConversionPurpose,
    ) -> Money:
        if purpose == ConversionPurpose.CALCULATION:
            return money
        if minor_units is None:
            raise CurrencyPrecisionUndefined(
                f"No minor units configured for {money.currency}."
            )
        if not 0 <= minor_units <= 9:
            raise CurrencyPrecisionUndefined("Invalid minor units.")
        with localcontext() as context:
            context.prec = max(
                38,
                money.amount.adjusted() + minor_units + 4,
                len(money.amount.as_tuple().digits) + 4,
            )
            return Money(
                money.amount.quantize(
                    Decimal(1).scaleb(-minor_units), rounding=rounding_mode.value
                ),
                money.currency,
            )
