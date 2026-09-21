from pydantic import Field
from typing import Literal
from src.modules.currency.presentation.http.request import RequestModel


class PolicyRequest(RequestModel):
    """Validated HTTP input for policy request."""

    default_transaction_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    provider_code: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
    rate_date_policy: Literal["exact", "previous_available"]
    rounding_mode: Literal["ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN", "ROUND_UP"]
    allow_cross_rate: bool
    bridge_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    business_timezone: str = Field(min_length=1, max_length=64)
    default_display_currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")


__all__ = ["PolicyRequest"]
