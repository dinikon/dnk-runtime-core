from datetime import datetime
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.inventory.application.stock_execution.query.list_stock_executions.dto import (
    ListStockExecutionsResultDTO,
)


class ListStockExecutionsItemResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    id: UUID
    document_id: UUID
    document_status: str
    document_version: int
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    operation_type: str
    executed_at: datetime
    posting_id: UUID | None
    line_count: int


class ListStockExecutionsResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    items: tuple[ListStockExecutionsItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListStockExecutionsResultDTO) -> Self:
        """Явно проверяет конкретный Application DTO своей схемой сериализации."""
        return cls.model_validate(dto, from_attributes=True)
