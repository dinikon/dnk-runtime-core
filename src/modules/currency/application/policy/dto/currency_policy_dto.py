from __future__ import annotations
from dataclasses import dataclass
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.policy.value_object.rounding_mode import RoundingMode
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencyPolicyDTO:
    """Immutable policy application result."""

    default_transaction_currency: CurrencyCodeVO
    provider_code: ProviderCode
    rate_date_policy: RateDatePolicy
    rounding_mode: RoundingMode
    allow_cross_rate: bool
    bridge_currency: CurrencyCodeVO
    business_timezone: str = "Europe/Kyiv"
    version: int = 1
    default_display_currency: CurrencyCodeVO | None = None

    @classmethod
    def from_entity(cls, value: CurrencyPolicy) -> "CurrencyPolicyDTO":
        return cls(
            default_transaction_currency=value.default_transaction_currency,
            provider_code=value.provider_code,
            rate_date_policy=value.rate_date_policy,
            rounding_mode=value.rounding_mode,
            allow_cross_rate=value.allow_cross_rate,
            bridge_currency=value.bridge_currency,
            business_timezone=value.business_timezone,
            version=value.version,
            default_display_currency=value.default_display_currency,
        )

    def to_entity(self) -> CurrencyPolicy:
        """Reconstitute validated policy for Currency's own domain services."""
        return CurrencyPolicy(
            self.default_transaction_currency,
            self.provider_code,
            self.rate_date_policy,
            self.rounding_mode,
            self.allow_cross_rate,
            self.bridge_currency,
            self.business_timezone,
            self.version,
            self.default_display_currency,
        )


__all__ = ["CurrencyPolicyDTO"]
