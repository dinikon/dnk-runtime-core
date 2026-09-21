from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencyInfo:
    """ISO directory metadata used to validate currencies and their precision."""

    code: CurrencyCodeVO
    name: str
    minor_units: int | None
    numeric_code: str | None = None
    symbol: str | None = None
    is_active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None


__all__ = ["CurrencyInfo"]
