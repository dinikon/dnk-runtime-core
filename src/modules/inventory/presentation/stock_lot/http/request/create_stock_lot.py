from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StrictStr

from src.modules.inventory.presentation.stock_lot.http.request.calendar_date import (
    parse_calendar_date,
)


class CreateStockLotRequest(BaseModel):
    """Принимает ручной строковый номер и необязательные даты ISO без времени."""

    model_config = ConfigDict(extra="forbid")
    number: StrictStr
    manufactured_on: Annotated[date | None, BeforeValidator(parse_calendar_date)] = None
    expires_on: Annotated[date | None, BeforeValidator(parse_calendar_date)] = None
