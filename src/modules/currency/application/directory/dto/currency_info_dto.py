from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.modules.currency.domain.directory.entity import CurrencyInfo
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencyInfoDTO:
    """Immutable directory application result."""

    code: CurrencyCodeVO
    name: str
    minor_units: int | None
    numeric_code: str | None = None
    symbol: str | None = None
    is_active: bool = True
    valid_from: date | None = None
    valid_to: date | None = None

    @classmethod
    def from_entity(cls, value: CurrencyInfo) -> "CurrencyInfoDTO":
        return cls(
            code=value.code,
            name=value.name,
            minor_units=value.minor_units,
            numeric_code=value.numeric_code,
            symbol=value.symbol,
            is_active=value.is_active,
            valid_from=value.valid_from,
            valid_to=value.valid_to,
        )


__all__ = ["CurrencyInfoDTO"]
