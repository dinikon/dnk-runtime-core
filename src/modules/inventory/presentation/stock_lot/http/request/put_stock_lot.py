from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict

from src.modules.inventory.presentation.stock_lot.http.request.calendar_date import (
    parse_calendar_date,
)


class PutStockLotRequest(BaseModel):
    """Требует обе редактируемые даты, разрешая явный null для очищения."""

    model_config = ConfigDict(extra="forbid")
    manufactured_on: Annotated[date | None, BeforeValidator(parse_calendar_date)]
    expires_on: Annotated[date | None, BeforeValidator(parse_calendar_date)]
