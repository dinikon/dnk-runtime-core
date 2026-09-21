from datetime import date
from pydantic import Field
from src.modules.currency.presentation.http.request import RequestModel


class RateRequest(RequestModel):
    """Validated HTTP input for rate request."""

    source_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    target_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    rate: str = Field(pattern=r"^\d+(\.\d+)?$", max_length=100)
    effective_date: date


__all__ = ["RateRequest"]
