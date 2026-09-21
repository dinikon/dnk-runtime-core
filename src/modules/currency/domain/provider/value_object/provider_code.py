from __future__ import annotations
from dataclasses import dataclass
from src.modules.currency.domain.error import CurrencyError


@dataclass(frozen=True, slots=True)
class ProviderCode:
    """Normalized identifier of a local or externally registered rate source."""

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


__all__ = ["ProviderCode"]
