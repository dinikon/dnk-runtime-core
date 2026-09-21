from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError


class CurrencyDisabled(CurrencyError):
    """Currency cannot be used in a new operation for this tenant."""

    code = "currency_disabled"


__all__ = ["CurrencyDisabled"]
