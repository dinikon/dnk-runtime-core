from datetime import date
from pydantic import Field
from typing import Literal
from src.modules.currency.presentation.http.request import RequestModel


class ConvertRequest(RequestModel):
    """Validated HTTP input for convert request."""

    amount: str = Field(pattern=r"^-?\d+(\.\d+)?$", max_length=100)
    source_currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    target_currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    business_date: date
    purpose: Literal["calculation", "booking", "display"] = "calculation"
    precision: int | None = Field(default=None, ge=0, strict=True)


__all__ = ["ConvertRequest"]
