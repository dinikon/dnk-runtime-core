from typing import Any, Sequence
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)


class StockDocumentMapper:
    """Преобразует собственное сохранённое состояние без SQL и текущих справочников."""

    @staticmethod
    def to_insert_values(document: StockDocument) -> dict[str, Any]:
        """Извлекает реквизиты без новых ID и подмены версии."""
        return dict(
            id=document.id.uuid,
            operation_type=document.operation_type.value,
            warehouse_id=document.warehouse_id.uuid,
            owner_id=document.owner_id.uuid,
            status=document.status.value,
            source_system=(
                document.source.system if document.source is not None else None
            ),
            source_reference=(
                document.source.reference if document.source is not None else None
            ),
            source_version=(
                document.source.version if document.source is not None else None
            ),
            created_at=document.created_at,
            updated_at=document.updated_at,
            version=document.version,
        )

    @staticmethod
    def to_update_values(document: StockDocument) -> dict[str, Any]:
        """Подготавливает реквизиты существующего корня без изменения его ID."""
        values = StockDocumentMapper.to_insert_values(document)
        del values["id"]
        return values

    @staticmethod
    def line_matches(
        model: StockDocumentLineModel, line: StockDocumentLine, position: int
    ) -> bool:
        """Сравнивает сохранённые скаляры строки, не вызывая бизнес-проверок."""
        return (
            model.position,
            model.inventory_item_id,
            model.sku,
            model.base_uom,
            model.planned_qty,
            model.source_quantity,
            model.source_uom,
            model.factor_to_base,
            model.executed_qty,
            model.source_system,
            model.source_reference,
        ) == (
            position,
            line.inventory_item_id.uuid,
            line.sku.value,
            line.base_uom.value,
            line.planned_qty.value,
            line.conversion.quantity.value,
            line.conversion.uom.value,
            line.conversion.factor_to_base,
            line.executed_qty.value,
            line.source.system if line.source is not None else None,
            line.source.reference if line.source is not None else None,
        )

    @staticmethod
    def to_line_insert_values(document: StockDocument) -> list[dict[str, Any]]:
        """Сохраняет порядок, точные количества и исходный пересчёт строк."""
        if any(line.adjustment is not None for line in document.lines):
            raise NotImplementedError(
                "Хранение оснований ADJUSTMENT добавляется отдельным срезом."
            )
        return [
            dict(
                id=line.id.uuid,
                document_id=document.id.uuid,
                position=position,
                inventory_item_id=line.inventory_item_id.uuid,
                sku=line.sku.value,
                base_uom=line.base_uom.value,
                planned_qty=line.planned_qty.value,
                source_quantity=line.conversion.quantity.value,
                source_uom=line.conversion.uom.value,
                factor_to_base=line.conversion.factor_to_base,
                executed_qty=line.executed_qty.value,
                source_system=line.source.system if line.source is not None else None,
                source_reference=(
                    line.source.reference if line.source is not None else None
                ),
            )
            for position, line in enumerate(document.lines)
        ]

    @staticmethod
    def to_domain(
        model: StockDocumentModel, lines: Sequence[StockDocumentLineModel]
    ) -> StockDocument:
        """Восстанавливает исторические SKU, единицы и версию без текущих настроек."""
        children = tuple(
            StockDocumentLine.restore(
                identifier=StockDocumentLineIdVO(line.id),
                inventory_item_id=InventoryItemIdVO(line.inventory_item_id),
                sku=SkuVO(line.sku),
                base_uom=UomCodeVO(line.base_uom),
                planned_qty=QuantityVO(line.planned_qty),
                conversion=QuantityConversionSnapshotVO(
                    QuantityVO(line.source_quantity),
                    UomCodeVO(line.source_uom),
                    line.factor_to_base,
                ),
                executed_qty=QuantityVO(line.executed_qty),
                source=(
                    DocumentLineSourceVO(line.source_system, line.source_reference)
                    if line.source_system is not None
                    and line.source_reference is not None
                    else None
                ),
                adjustment=None,
            )
            for line in lines
        )
        return StockDocument.restore(
            identifier=StockDocumentIdVO(model.id),
            operation_type=StockOperationType(model.operation_type),
            warehouse_id=WarehouseIdVO(model.warehouse_id),
            owner_id=StockOwnerIdVO(model.owner_id),
            status=StockDocumentStatus(model.status),
            source=(
                DocumentSourceVO(
                    model.source_system, model.source_reference, model.source_version
                )
                if model.source_system is not None
                and model.source_reference is not None
                else None
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            lines=children,
        )
