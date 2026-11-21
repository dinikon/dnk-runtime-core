from typing import Literal, Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)


class ListIssueDocumentsRequest(BaseModel):
    """Проверяет страницу, диапазон дат с часовым поясом и серверные фильтры."""

    model_config = ConfigDict(extra="forbid")
    search: str | None = Field(default=None, max_length=128)
    warehouse_id: UUID | None = None
    owner_id: UUID | None = None
    status: StockDocumentStatus | Literal["ALL"] = StockDocumentStatus.DRAFT
    created_from: AwareDatetime | None = None
    created_to: AwareDatetime | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def require_ordered_dates(self) -> Self:
        """Отклоняет перевёрнутый диапазон на транспортной границе."""
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("Начало периода не должно быть позже окончания.")
        return self
