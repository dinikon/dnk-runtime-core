from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemDocumentSnapshotError,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentContextError,
    InvalidStockDocumentLineError,
    StockDocumentLineConflictError,
)
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockDocumentConfirmationPolicy:
    """Проверяет подтверждение плана по активному складу и ровно нужным снимкам товаров."""

    @staticmethod
    def ensure_warehouse(
        *, warehouse_id: WarehouseIdVO, warehouse: WarehouseSnapshot
    ) -> None:
        """Требует типизированный снимок того же активного склада без загрузки его локаций."""
        if not isinstance(warehouse, WarehouseSnapshot):
            raise InvalidWarehouseSnapshotError("Нужен снимок склада документа.")
        warehouse.ensure_valid()
        if not isinstance(warehouse_id, WarehouseIdVO) or warehouse_id != warehouse.id:
            raise InvalidStockDocumentContextError(
                "Снимок склада не соответствует документу."
            )
        if not warehouse.is_active:
            raise WarehouseInactiveError(
                "Неактивный склад недоступен для нового или подтверждаемого плана."
            )

    @staticmethod
    def ensure_confirmable(
        *,
        warehouse_id: WarehouseIdVO,
        warehouse: WarehouseSnapshot,
        lines: tuple[StockDocumentLine, ...],
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
    ) -> None:
        """Проверяет непустой план, уникальность строк и актуальные настройки каждого товара."""
        StockDocumentConfirmationPolicy.ensure_warehouse(
            warehouse_id=warehouse_id, warehouse=warehouse
        )
        if not isinstance(lines, tuple):
            raise InvalidStockDocumentLineError("Строки плана передаются в tuple.")
        if not lines:
            raise EmptyStockDocumentError("Нельзя подтвердить документ без строк.")
        if not isinstance(inventory_items, tuple):
            raise InvalidStockDocumentContextError("Нужен tuple снимков товаров плана.")
        by_item = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemDocumentSnapshot):
                raise InvalidInventoryItemDocumentSnapshotError(
                    "Нужны снимки товаров для документа."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InvalidStockDocumentContextError(
                    "Снимок каждого товара передаётся один раз."
                )
            by_item[item.inventory_item_id] = item
        line_ids = set()
        item_ids = set()
        for line in lines:
            if not isinstance(line, StockDocumentLine):
                raise InvalidStockDocumentLineError(
                    "Нужны типизированные плановые строки."
                )
            line.ensure_valid()
            if line.id in line_ids:
                raise StockDocumentLineConflictError(
                    "ID плановых строк должны быть уникальны."
                )
            line_ids.add(line.id)
            item_ids.add(line.inventory_item_id)
            item = by_item.get(line.inventory_item_id)
            if item is None:
                raise InvalidStockDocumentContextError(
                    "Отсутствует снимок товара одной из строк."
                )
            line.ensure_compatible(item)
        if item_ids != set(by_item):
            raise InvalidStockDocumentContextError(
                "Лишние снимки товаров не допускаются."
            )
