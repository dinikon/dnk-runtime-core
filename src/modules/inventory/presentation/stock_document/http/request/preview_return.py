from src.modules.inventory.domain.value_object.stock_status import StockStatus
from typing import Annotated, Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator


class PreviewReturnLineRequest(BaseModel):
    """Принимает ID источника, не позволяя подменить его учётные измерения."""

    model_config = ConfigDict(extra="forbid")
    client_line_id: UUID
    document_line_id: UUID
    source_position_id: UUID | None = None
    location_id: UUID | None = None
    stock_status: StockStatus | None = None
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def exactly_one_side(self) -> Self:
        """Принимает существующий источник либо явные адрес и состояние приёмки."""
        if self.source_position_id is not None:
            if self.location_id is not None or self.stock_status is not None:
                raise ValueError("Для расхода передайте только исходную позицию.")
        elif self.location_id is None or self.stock_status is None:
            raise ValueError("Для приёмки укажите адрес и состояние.")
        return self


class PreviewReturnRequest(BaseModel):
    """Ограничивает форму команды; достаточность и шаг количества проверяет Domain."""

    model_config = ConfigDict(extra="forbid")
    expected_version: StrictInt = Field(ge=0)
    lines: list[PreviewReturnLineRequest] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_client_keys(self) -> Self:
        """Требует уникальный ключ каждого распределения, включая повтор источника."""
        keys = [line.client_line_id for line in self.lines]
        if len(keys) != len(set(keys)):
            raise ValueError("Ключ фактической строки должен быть уникальным.")
        return self
