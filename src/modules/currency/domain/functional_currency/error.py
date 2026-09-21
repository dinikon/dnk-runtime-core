from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.policy.error import CurrencyConflict


class FunctionalCurrencyNotConfigured(CurrencyError):
    """No functional currency period covers the requested business date."""

    code = "functional_currency_not_configured"


class FunctionalCurrencyPeriodOverlap(CurrencyConflict):
    """A proposed functional period intersects an existing interval."""

    code = "functional_currency_period_overlap"


class FunctionalCurrencyChangeNotAllowed(CurrencyConflict):
    """A functional currency change violates the append-only future timeline."""

    code = "functional_currency_change_not_allowed"


__all__ = [
    "FunctionalCurrencyChangeNotAllowed",
    "FunctionalCurrencyNotConfigured",
    "FunctionalCurrencyPeriodOverlap",
]
