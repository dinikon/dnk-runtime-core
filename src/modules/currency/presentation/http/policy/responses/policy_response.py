from pydantic import BaseModel
from src.modules.currency.application.policy.dto.currency_policy_dto import (
    CurrencyPolicyDTO,
)


class PolicyResponse(BaseModel):
    """Validated HTTP output for policy response."""

    default_transaction_currency: str
    provider_code: str
    rate_date_policy: str
    rounding_mode: str
    allow_cross_rate: bool
    bridge_currency: str
    business_timezone: str
    version: int
    default_display_currency: str | None

    @classmethod
    def from_dto(cls, policy: CurrencyPolicyDTO):
        return cls(
            default_transaction_currency=str(policy.default_transaction_currency),
            provider_code=str(policy.provider_code),
            rate_date_policy=policy.rate_date_policy.value,
            rounding_mode=policy.rounding_mode.value,
            allow_cross_rate=policy.allow_cross_rate,
            bridge_currency=str(policy.bridge_currency),
            business_timezone=policy.business_timezone,
            version=policy.version,
            default_display_currency=(
                str(policy.default_display_currency)
                if policy.default_display_currency
                else None
            ),
        )


__all__ = ["PolicyResponse"]
