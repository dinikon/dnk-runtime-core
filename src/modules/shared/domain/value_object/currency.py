from __future__ import annotations

from dataclasses import dataclass
import re

from .money_errors import InvalidCurrencyCodeError


@dataclass(frozen=True, slots=True)
class CurrencyCodeVO:
    """Syntactic identifier; currency membership belongs to the directory."""

    value: str

    def __post_init__(self):
        if not isinstance(self.value, str):
            raise InvalidCurrencyCodeError("Currency code must be a string.")
        value = self.value.strip()
        if re.fullmatch(r"[A-Za-z]{3}", value) is None:
            raise InvalidCurrencyCodeError(
                "Currency code must contain three ASCII letters."
            )
        object.__setattr__(self, "value", value.upper())

    @classmethod
    def from_value(cls, value: str | CurrencyCodeVO) -> CurrencyCodeVO:
        return value if isinstance(value, cls) else cls(value)

    def __str__(self):
        return self.value


__all__ = ["InvalidCurrencyCodeError", "CurrencyCodeVO"]
