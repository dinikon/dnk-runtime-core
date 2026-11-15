from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.dto import (
    GetInternalMoveDocumentResultDTO,
)


class GetInternalMoveDocumentLineResponse(BaseModel):
    """Показывает точный исторический пересчёт плановой строки."""

    id: UUID
    position: int
    inventory_item_id: UUID
    sku: str
    base_uom: str
    planned_qty: Decimal
    source_quantity: Decimal
    source_uom: str
    factor_to_base: Decimal
    executed_qty: Decimal
    remaining_qty: Decimal


class GetInternalMoveDocumentResponse(BaseModel):
    """Возвращает конкретный HTTP-контракт перемещения."""

    id: UUID
    operation_type: StockOperationType
    status: StockDocumentStatus
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    source_system: str | None
    source_reference: str | None
    source_version: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    lines: list[GetInternalMoveDocumentLineResponse]

    @classmethod
    def from_dto(
        cls, dto: GetInternalMoveDocumentResultDTO
    ) -> "GetInternalMoveDocumentResponse":
        """Явно преобразует результат собственного сценария."""
        return cls(
            id=dto.id,
            operation_type=dto.operation_type,
            status=dto.status,
            warehouse_id=dto.warehouse_id,
            warehouse_code=dto.warehouse_code,
            warehouse_name=dto.warehouse_name,
            owner_id=dto.owner_id,
            owner_name=dto.owner_name,
            source_system=dto.source_system,
            source_reference=dto.source_reference,
            source_version=dto.source_version,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            version=dto.version,
            lines=[
                GetInternalMoveDocumentLineResponse(
                    id=line.id,
                    position=line.position,
                    inventory_item_id=line.inventory_item_id,
                    sku=line.sku,
                    base_uom=line.base_uom,
                    planned_qty=line.planned_qty,
                    source_quantity=line.source_quantity,
                    source_uom=line.source_uom,
                    factor_to_base=line.factor_to_base,
                    executed_qty=line.executed_qty,
                    remaining_qty=line.remaining_qty,
                )
                for line in dto.lines
            ],
        )
