from pydantic import BaseModel, ConfigDict, Field, model_validator
from uuid import UUID
from typing import Self


class UpdateCatalogCategoryRequest(BaseModel):
    """Различает перенос в корень и сохранение текущего родителя."""

    model_config = ConfigDict(extra="forbid")
    parent_id: UUID | None = None
    translations: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        """Требует хотя бы одно изменение положения или названия."""
        if "parent_id" not in self.model_fields_set and not self.translations:
            raise ValueError("Укажите перевод или нового родителя.")
        return self
