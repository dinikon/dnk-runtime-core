from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.prepare_status_change.dto import (
    PrepareStatusChangeResultDTO,
)


class PrepareStatusChangeLineResponse(BaseModel):
    """Передаёт числовое основание и актуальные режимы одной строки."""

    document_line_id: UUID
    position: int
    planned_quantity: Decimal
    executed_quantity: Decimal
    inventory_item_id: UUID
    sku: str
    base_uom: str
    current_base_uom: str
    remaining_quantity: Decimal
    quantity_step: Decimal
    tracking_mode: str
    expiration_mode: str


class PrepareStatusChangeResponse(BaseModel):
    """Сериализует точный остаток плана для формы изменения состояния."""

    document_id: UUID
    version: int
    status: str
    warehouse_id: UUID
    reason: str
    target_status: str
    lines: list[PrepareStatusChangeLineResponse]

    @classmethod
    def from_dto(
        cls, dto: PrepareStatusChangeResultDTO
    ) -> "PrepareStatusChangeResponse":
        """Явно преобразует собственный DTO без текущих цен и чисел floating point."""
        return cls(
            document_id=dto.document_id,
            version=dto.version,
            status=dto.status,
            warehouse_id=dto.warehouse_id,
            reason=dto.reason,
            target_status=dto.target_status,
            lines=[
                PrepareStatusChangeLineResponse(
                    document_line_id=v.document_line_id,
                    position=v.position,
                    planned_quantity=v.planned_quantity,
                    executed_quantity=v.executed_quantity,
                    inventory_item_id=v.inventory_item_id,
                    sku=v.sku,
                    base_uom=v.base_uom,
                    current_base_uom=v.current_base_uom,
                    remaining_quantity=v.remaining_quantity,
                    quantity_step=v.quantity_step,
                    tracking_mode=v.tracking_mode,
                    expiration_mode=v.expiration_mode,
                )
                for v in dto.lines
            ],
        )
