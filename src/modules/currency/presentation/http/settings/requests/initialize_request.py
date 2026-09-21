from datetime import date
from pydantic import Field
from src.modules.currency.presentation.http.policy.requests.policy_request import (
    PolicyRequest,
)


class InitializeRequest(PolicyRequest):
    """Validated HTTP input for initialize request."""

    enabled_currencies: list[str] = Field(min_length=1, max_length=200)
    functional_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    valid_from: date
    reason: str = Field(min_length=1, max_length=1000)


__all__ = ["InitializeRequest"]
