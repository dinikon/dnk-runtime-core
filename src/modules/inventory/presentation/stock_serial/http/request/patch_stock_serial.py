from typing import Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StrictStr, model_validator


class PatchStockSerialRequest(BaseModel):
    """Принимает непустой PATCH; пропуск партии сохраняет связь, null очищает её."""

    model_config = ConfigDict(extra="forbid")
    number: StrictStr = ""
    lot_id: UUID | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Запрещает пустой PATCH, не проверяя предметную допустимость значений."""
        if not self.model_fields_set:
            raise ValueError("Укажите номер или партию для изменения.")
        return self
