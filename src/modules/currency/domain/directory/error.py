from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError


class CurrencyNotFound(CurrencyError):
    """Requested currency is absent or inactive in the global directory."""

    code = "currency_not_found"


__all__ = ["CurrencyNotFound"]
