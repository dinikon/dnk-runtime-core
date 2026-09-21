from __future__ import annotations
from dataclasses import dataclass
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencyPair:
    """Ordered source and target currencies with no implicit direction reversal."""

    source: CurrencyCodeVO
    target: CurrencyCodeVO

    def inverse(self):
        return CurrencyPair(self.target, self.source)


__all__ = ["CurrencyPair"]
