from __future__ import annotations
from src.modules.shared.domain.domain_error import DomainError


class CurrencyError(DomainError):
    """Base error for invalid currency rules and values."""

    code = "currency_error"


__all__ = ["CurrencyError"]
