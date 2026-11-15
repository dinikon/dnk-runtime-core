from typing import Sequence
from decimal import Decimal
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.dto import (
    GetInternalMoveDocumentResultDTO,
    GetInternalMoveDocumentLineDTO,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.dto import (
    InternalMoveDocumentListItemDTO,
)


class InternalMoveDocumentQueryMapper:
    """Строит конкретные проекции без восстановления агрегатов."""

    @staticmethod
    def to_details(
        model: StockDocumentModel,
        warehouse: WarehouseModel,
        lines: Sequence[tuple[StockDocumentLineModel, Decimal]],
    ) -> GetInternalMoveDocumentResultDTO:
        """Показывает сохранённый план, а не актуальные параметры товара."""
        return GetInternalMoveDocumentResultDTO(
            id=model.id,
            operation_type=StockOperationType(model.operation_type),
            status=StockDocumentStatus(model.status),
            warehouse_id=model.warehouse_id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=model.owner_id,
            owner_name=None,
            source_system=model.source_system,
            source_reference=model.source_reference,
            source_version=model.source_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            lines=tuple(
                GetInternalMoveDocumentLineDTO(
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
                    remaining_qty=remaining,
                )
                for line, remaining in lines
            ),
        )

    @staticmethod
    def to_list_item(
        model: StockDocumentModel, warehouse: WarehouseModel, line_count: int
    ) -> InternalMoveDocumentListItemDTO:
        """Возвращает строку списка с количеством плановых строк."""
        return InternalMoveDocumentListItemDTO(
            id=model.id,
            operation_type=StockOperationType(model.operation_type),
            status=StockDocumentStatus(model.status),
            warehouse_id=model.warehouse_id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=model.owner_id,
            owner_name=None,
            source_system=model.source_system,
            source_reference=model.source_reference,
            source_version=model.source_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            line_count=line_count,
        )
