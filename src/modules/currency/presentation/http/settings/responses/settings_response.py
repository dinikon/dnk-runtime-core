from datetime import date, datetime
from pydantic import BaseModel
from src.modules.currency.presentation.http.functional_currency.responses.period_response import (
    PeriodResponse,
)
from src.modules.currency.presentation.http.policy.responses.policy_response import (
    PolicyResponse,
)
from src.modules.currency.presentation.http.provider.responses.provider_status_response import (
    ProviderStatusResponse,
)


class SettingsResponse(BaseModel):
    """Validated HTTP output for settings response."""

    configured: bool
    policy: PolicyResponse | None
    enabled_currencies: list[str]
    periods: list[PeriodResponse]
    functional_currency: str | None
    future_functional_currency: str | None
    business_date: date
    provider_status: ProviderStatusResponse
    permissions: list[str]
    default_display_currency: str | None
    next_business_day_at: datetime


class ActionResponse(BaseModel):
    """Validated HTTP output for action response."""

    ok: bool = True


__all__ = ["SettingsResponse", "ActionResponse"]
