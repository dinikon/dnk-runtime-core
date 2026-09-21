from pydantic import Field
from src.modules.currency.presentation.http.policy.requests.policy_request import (
    PolicyRequest,
)


class ConfigureRequest(PolicyRequest):
    """Validated HTTP input for configure request."""

    expected_version: int = Field(ge=1)


__all__ = ["ConfigureRequest"]
