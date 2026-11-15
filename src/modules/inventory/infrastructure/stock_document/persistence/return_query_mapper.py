from uuid import UUID
from src.modules.inventory.infrastructure.persistence.models.stock_document_return import (
    StockDocumentReturnModel,
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
from src.modules.inventory.application.stock_document.query.get_return_document.dto import (
    GetReturnDocumentResultDTO,
    GetReturnDocumentLineDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.dto import (
    ReturnDocumentListItemDTO,
)


class ReturnDocumentQueryMapper:
    """Строит конкретные проекции без восстановления агрегатов."""

    @staticmethod
    def to_details(
        model: StockDocumentModel,
        warehouse: WarehouseModel,
        details: StockDocumentReturnModel,
        lines: Sequence[tuple[StockDocumentLineModel, Decimal, UUID]],
    ) -> GetReturnDocumentResultDTO:
        """Показывает сохранённый план, а не актуальные параметры товара."""
        return GetReturnDocumentResultDTO(
            id=model.id,
            operation_type=StockOperationType(model.operation_type),
            status=StockDocumentStatus(model.status),
            warehouse_id=model.warehouse_id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=model.owner_id,
            owner_name=None,
            reason=details.reason,
            direction=details.direction,
            origin_execution_id=details.origin_execution_id,
            source_system=model.source_system,
            source_reference=model.source_reference,
            source_version=model.source_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            lines=tuple(
                GetReturnDocumentLineDTO(
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
                    origin_execution_line_id=origin_line_id,
                )
                for line, remaining, origin_line_id in lines
            ),
        )

    @staticmethod
    def to_list_item(
        model: StockDocumentModel,
        warehouse: WarehouseModel,
        details: StockDocumentReturnModel,
        line_count: int,
    ) -> ReturnDocumentListItemDTO:
        """Возвращает строку списка с количеством плановых строк."""
        return ReturnDocumentListItemDTO(
            id=model.id,
            operation_type=StockOperationType(model.operation_type),
            status=StockDocumentStatus(model.status),
            warehouse_id=model.warehouse_id,
            warehouse_code=warehouse.code,
            warehouse_name=warehouse.name,
            owner_id=model.owner_id,
            owner_name=None,
            reason=details.reason,
            direction=details.direction,
            origin_execution_id=details.origin_execution_id,
            source_system=model.source_system,
            source_reference=model.source_reference,
            source_version=model.source_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            line_count=line_count,
        )
