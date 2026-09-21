from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError


class CurrencyPrecisionUndefined(CurrencyError):
    """Booking precision cannot be determined from the request or directory."""

    code = "currency_precision_undefined"


__all__ = ["CurrencyPrecisionUndefined"]
