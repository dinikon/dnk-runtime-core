from datetime import datetime
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.inventory.application.stock_posting.query.list_stock_postings.dto import (
    ListStockPostingsResultDTO,
)


class ListStockPostingsItemResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    id: UUID
    execution_id: UUID
    document_id: UUID
    document_status: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    operation_type: str
    posted_at: datetime
    entry_count: int


class ListStockPostingsResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    items: tuple[ListStockPostingsItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListStockPostingsResultDTO) -> Self:
        """Явно проверяет конкретный Application DTO своей схемой сериализации."""
        return cls.model_validate(dto, from_attributes=True)
