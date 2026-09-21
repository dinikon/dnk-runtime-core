from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError


class CurrencyPolicyNotConfigured(CurrencyError):
    """Organization has not explicitly saved initial currency settings."""

    code = "policy_not_configured"


class CurrencyConflict(CurrencyError):
    """Expected policy version or protected currency rule conflicts with current state."""

    code = "currency_conflict"


__all__ = ["CurrencyConflict", "CurrencyPolicyNotConfigured"]
