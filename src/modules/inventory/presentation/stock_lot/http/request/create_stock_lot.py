from datetime import date
import re

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator


class CreateStockLotRequest(BaseModel):
    """Принимает ручной строковый номер и календарные даты ISO без времени и coercion."""

    model_config = ConfigDict(extra="forbid")
    number: StrictStr
    manufactured_on: date | None = None
    expires_on: date | None = None

    @field_validator("manufactured_on", "expires_on", mode="before")
    @classmethod
    def calendar_date(cls, value: object) -> date | None:
        """Разрешает только null либо строку YYYY-MM-DD, отклоняя datetime и числа."""
        if value is None:
            return None
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
        ):
            raise ValueError("Укажите календарную дату YYYY-MM-DD без времени.")
        return date.fromisoformat(value)
