from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.value_object.rate_derivation import (
    RateDerivation,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ConversionSnapshot:
    """Immutable conversion provenance owned and stored by the consuming document."""

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
    purpose: str | None = None
    precision: int | None = None
    rounding_mode: str | None = None
    calculation_precision: int | None = None
    minor_units: int | None = None


__all__ = ["ConversionSnapshot"]
