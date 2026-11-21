from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.list_write_off_executions.dto import (
    ListWriteOffExecutionsResultDTO,
)


class ListWriteOffExecutionLineResponse(BaseModel):
    """Показывает принятое количество отдельной строки без смешения товаров и единиц."""

    document_line_id: UUID
    position: int
    sku: str
    base_uom: str
    quantity: Decimal
    allocation_count: int


class ListWriteOffExecutionItemResponse(BaseModel):
    """Показывает факт и статус на момент его проведения."""

    execution_id: UUID
    posting_id: UUID
    posted_at: datetime
    document_version_after: int
    document_status: str
    reason: str
    line_count: int
    lines: list[ListWriteOffExecutionLineResponse]


class ListWriteOffExecutionsResponse(BaseModel):
    """Сериализует страницу истории документа."""

    items: list[ListWriteOffExecutionItemResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(
        cls, dto: ListWriteOffExecutionsResultDTO
    ) -> "ListWriteOffExecutionsResponse":
        """Явно преобразует собственный результат чтения."""
        return cls(
            items=[
                ListWriteOffExecutionItemResponse(
                    execution_id=v.execution_id,
                    posting_id=v.posting_id,
                    posted_at=v.posted_at,
                    document_version_after=v.document_version_after,
                    document_status=v.document_status,
                    reason=v.reason,
                    line_count=v.line_count,
                    lines=[
                        ListWriteOffExecutionLineResponse(
                            document_line_id=line.document_line_id,
                            position=line.position,
                            sku=line.sku,
                            base_uom=line.base_uom,
                            quantity=line.quantity,
                            allocation_count=line.allocation_count,
                        )
                        for line in v.lines
                    ],
                )
                for v in dto.items
            ],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
