from __future__ import annotations
from dataclasses import dataclass
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError
from src.modules.currency.domain.error import CurrencyError
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencyPolicy:
    """Immutable organization policy for source, date, precision and currency defaults."""

    default_transaction_currency: CurrencyCodeVO
    provider_code: ProviderCode
    rate_date_policy: RateDatePolicy
    rounding_mode: RoundingMode
    allow_cross_rate: bool
    bridge_currency: CurrencyCodeVO
    business_timezone: str = "Europe/Kyiv"
    version: int = 1
    default_display_currency: CurrencyCodeVO | None = None

    def __post_init__(self):
        try:
            ZoneInfo(self.business_timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise CurrencyError("Unknown business timezone.") from None
        if self.version < 1:
            raise CurrencyError("Policy version must be positive.")


__all__ = ["CurrencyPolicy"]
