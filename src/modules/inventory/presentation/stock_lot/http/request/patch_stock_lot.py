from datetime import date
from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from src.modules.inventory.presentation.stock_lot.http.request.calendar_date import (
    parse_calendar_date,
)


class PatchStockLotRequest(BaseModel):
    """Принимает непустой набор дат, отличая пропуск от явного очищения."""

    model_config = ConfigDict(extra="forbid")
    manufactured_on: Annotated[date | None, BeforeValidator(parse_calendar_date)] = None
    expires_on: Annotated[date | None, BeforeValidator(parse_calendar_date)] = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Запрещает пустой PATCH, сохраняя явный null как намерение очистить дату."""
        if not self.model_fields_set:
            raise ValueError("Укажите хотя бы одну дату для изменения или очищения.")
        return self
