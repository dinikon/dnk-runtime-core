from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.dto import (
    ListWriteOffDocumentsResultDTO,
)


class WriteOffDocumentListItemResponse(BaseModel):
    """Представляет одну строку страницы списаний."""

    id: UUID
    operation_type: StockOperationType
    status: StockDocumentStatus
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    reason: str
    source_system: str | None
    source_reference: str | None
    source_version: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    line_count: int


class ListWriteOffDocumentsResponse(BaseModel):
    """Возвращает страницу и количество по одним фильтрам."""

    items: list[WriteOffDocumentListItemResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(
        cls, dto: ListWriteOffDocumentsResultDTO
    ) -> "ListWriteOffDocumentsResponse":
        """Явно преобразует DTO страницы без универсального response."""
        return cls(
            items=[
                WriteOffDocumentListItemResponse(
                    id=item.id,
                    operation_type=item.operation_type,
                    status=item.status,
                    warehouse_id=item.warehouse_id,
                    warehouse_code=item.warehouse_code,
                    warehouse_name=item.warehouse_name,
                    owner_id=item.owner_id,
                    owner_name=item.owner_name,
                    reason=item.reason,
                    source_system=item.source_system,
                    source_reference=item.source_reference,
                    source_version=item.source_version,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    version=item.version,
                    line_count=item.line_count,
                )
                for item in dto.items
            ],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
