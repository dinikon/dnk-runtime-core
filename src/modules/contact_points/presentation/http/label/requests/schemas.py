from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator


class CreateLabelRequest(BaseModel):
    """Параметры новой подписи без tenant/actor из клиента."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["phone", "email"]
    name: str


class UpdateLabelRequest(BaseModel):
    """Частичное изменение имени и активности; явный null запрещён."""

    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Поля настройки не могут быть null.")
        return self


__all__ = ["CreateLabelRequest", "UpdateLabelRequest"]
