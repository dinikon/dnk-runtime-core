from typing import Annotated, Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator


class PreviewStatusChangeLineRequest(BaseModel):
    """Принимает ID источника, не позволяя подменить его учётные измерения."""

    model_config = ConfigDict(extra="forbid")
    client_line_id: UUID
    document_line_id: UUID
    source_position_id: UUID
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]


class PreviewStatusChangeRequest(BaseModel):
    """Ограничивает форму команды; достаточность и шаг количества проверяет Domain."""

    model_config = ConfigDict(extra="forbid")
    expected_version: StrictInt = Field(ge=0)
    lines: list[PreviewStatusChangeLineRequest] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_client_keys(self) -> Self:
        """Требует уникальный ключ каждого распределения, включая повтор источника."""
        keys = [line.client_line_id for line in self.lines]
        if len(keys) != len(set(keys)):
            raise ValueError("Ключ фактической строки должен быть уникальным.")
        return self
