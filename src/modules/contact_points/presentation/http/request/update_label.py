from pydantic import BaseModel, ConfigDict, model_validator


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
