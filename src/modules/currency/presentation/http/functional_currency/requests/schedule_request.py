from datetime import date
from pydantic import Field
from src.modules.currency.presentation.http.request import RequestModel


class ScheduleRequest(RequestModel):
    """Validated HTTP input for schedule request."""

    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    effective_from: date
    reason: str = Field(min_length=1, max_length=1000)


__all__ = ["ScheduleRequest"]
