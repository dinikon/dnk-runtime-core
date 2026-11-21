from typing import Literal, Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ListReceiptReferencesRequest(BaseModel):
    """Проверяет форму пагинации и наличие строки при поиске прослеживаемости."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["locations", "lots", "serials"]
    document_line_id: UUID | None = None
    lot_id: UUID | None = None
    search: str | None = Field(default=None, max_length=128)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def require_line_context(self) -> Self:
        """Для партий и экземпляров требует явную строку документа."""
        if self.kind != "locations" and self.document_line_id is None:
            raise ValueError("Нужна строка документа.")
        return self
