from src.modules.inventory.infrastructure.persistence.models.stock_document_status_change import (
    StockDocumentStatusChangeModel,
)
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
from src.modules.inventory.application.stock_document.query.get_status_change_document.dto import (
    GetStatusChangeDocumentResultDTO,
    GetStatusChangeDocumentLineDTO,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.dto import (
    StatusChangeDocumentListItemDTO,
)


class StatusChangeDocumentQueryMapper:
    """Строит конкретные проекции без восстановления агрегатов."""

    @staticmethod
    def to_details(
        model: StockDocumentModel,
        warehouse: WarehouseModel,
        details: StockDocumentStatusChangeModel,
        lines: Sequence[tuple[StockDocumentLineModel, Decimal]],
    ) -> GetStatusChangeDocumentResultDTO:
        """Показывает сохранённый план, а не актуальные параметры товара."""
        return GetStatusChangeDocumentResultDTO(
            id=model.id,
            operation_type=StockOperationType(model.operation_type),
            status=StockDocumentStatus(model.status),
            warehouse_id=model.warehouse_id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=model.owner_id,
            owner_name=None,
            reason=details.reason,
            target_status=details.target_status,
            source_system=model.source_system,
            source_reference=model.source_reference,
            source_version=model.source_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            lines=tuple(
                GetStatusChangeDocumentLineDTO(
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
        model: StockDocumentModel,
        warehouse: WarehouseModel,
        details: StockDocumentStatusChangeModel,
        line_count: int,
    ) -> StatusChangeDocumentListItemDTO:
        """Возвращает строку списка с количеством плановых строк."""
        return StatusChangeDocumentListItemDTO(
            id=model.id,
            operation_type=StockOperationType(model.operation_type),
            status=StockDocumentStatus(model.status),
            warehouse_id=model.warehouse_id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=model.owner_id,
            owner_name=None,
            reason=details.reason,
            target_status=details.target_status,
            source_system=model.source_system,
            source_reference=model.source_reference,
            source_version=model.source_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            line_count=line_count,
        )
