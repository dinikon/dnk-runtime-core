from pydantic import BaseModel, ConfigDict, Field, StrictInt
from typing import Annotated, Self
from uuid import UUID
from pydantic import StrictStr, model_validator


class ExistingWriteOffLineRequest(BaseModel):
    """Разрешает изменение количества и единицы собственной сохранённой строки."""

    model_config = ConfigDict(extra="forbid")
    id: UUID
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]


class NewWriteOffLineRequest(BaseModel):
    """Принимает товар и исходное количество новой строки без серверного ID."""

    model_config = ConfigDict(extra="forbid")
    inventory_item_id: UUID
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]


class PatchWriteOffDocumentRequest(BaseModel):
    """Проверяет транспортную форму действия и обязательную ожидаемую версию."""

    model_config = ConfigDict(extra="forbid")
    expected_version: StrictInt = Field(ge=0)
    lines: list[ExistingWriteOffLineRequest | NewWriteOffLineRequest] | None = Field(
        default=None, max_length=100
    )
    reason: Annotated[StrictStr, Field(min_length=1, max_length=1000)] | None = None

    @model_validator(mode="after")
    def unique_line_ids(self) -> Self:
        """Отклоняет повтор одного ID во входной коллекции до вызова Application."""
        if not self.model_fields_set.intersection({"lines", "reason"}):
            raise ValueError("Укажите причину или строки для изменения.")
        if any(
            name in self.model_fields_set and getattr(self, name) is None
            for name in ("lines", "reason")
        ):
            raise ValueError("Причина и строки не принимают null.")
        identifiers = [
            line.id
            for line in (self.lines or [])
            if isinstance(line, ExistingWriteOffLineRequest)
        ]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("ID существующей строки передаётся один раз.")
        return self
