from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_document.query.prepare_internal_move.dto import (
    PrepareInternalMoveResultDTO,
)


class PrepareInternalMoveLineResponse(BaseModel):
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


class PrepareInternalMoveResponse(BaseModel):
    """Сериализует точный остаток плана для формы перемещения."""

    document_id: UUID
    version: int
    status: str
    warehouse_id: UUID
    lines: list[PrepareInternalMoveLineResponse]

    @classmethod
    def from_dto(
        cls, dto: PrepareInternalMoveResultDTO
    ) -> "PrepareInternalMoveResponse":
        """Явно преобразует собственный DTO без текущих цен и чисел floating point."""
        return cls(
            document_id=dto.document_id,
            version=dto.version,
            status=dto.status,
            warehouse_id=dto.warehouse_id,
            lines=[
                PrepareInternalMoveLineResponse(
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
