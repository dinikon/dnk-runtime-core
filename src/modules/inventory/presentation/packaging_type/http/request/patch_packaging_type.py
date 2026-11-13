from typing import Self

from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr, model_validator
from pydantic.json_schema import SkipJsonSchema


class PatchPackagingTypeRequest(BaseModel):
    """Отличает пропущенные поля от null и сохраняет явно переданное false."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr | SkipJsonSchema[None] = None
    name: StrictStr | SkipJsonSchema[None] = None
    is_active: StrictBool | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Требует хотя бы одно изменяемое поле без явного null."""
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Нужен непустой набор изменяемых полей без null.")
        return self
