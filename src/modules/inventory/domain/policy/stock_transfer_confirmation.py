from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.stock_transfer.entity.transfer_line import (
    TransferLine,
)
from src.modules.inventory.domain.stock_transfer.error import (
    EmptyStockTransferError,
    InvalidStockTransferContextError,
    InvalidStockTransferLineError,
    StockTransferLineConflictError,
    StockTransferSameWarehouseError,
)
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferConfirmationPolicy:
    """Проверяет направление и актуальный состав плана межскладского перемещения без проверки запасов."""

    @staticmethod
    def ensure_warehouses(
        *,
        source_warehouse_id: WarehouseIdVO,
        destination_warehouse_id: WarehouseIdVO,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
    ) -> None:
        """Требует разные типизированные ID и снимки тех же двух активных складов без обязательных локаций."""
        if not isinstance(source_warehouse_id, WarehouseIdVO) or not isinstance(
            destination_warehouse_id, WarehouseIdVO
        ):
            raise InvalidStockTransferContextError(
                "Нужны типизированные ID обоих складов перемещения."
            )
        if source_warehouse_id == destination_warehouse_id:
            raise StockTransferSameWarehouseError(
                "Исходный и целевой склады должны различаться."
            )
        for identifier, warehouse in (
            (source_warehouse_id, source_warehouse),
            (destination_warehouse_id, destination_warehouse),
        ):
            if not isinstance(warehouse, WarehouseSnapshot):
                raise InvalidWarehouseSnapshotError(
                    "Нужны снимки исходного и целевого складов."
                )
            warehouse.ensure_valid()
            if identifier != warehouse.id:
                raise InvalidStockTransferContextError(
                    "Снимок склада не соответствует направлению перемещения."
                )
            if not warehouse.is_active:
                raise WarehouseInactiveError(
                    "Для создания или подтверждения нужны два активных склада."
                )

    @staticmethod
    def ensure_confirmable(
        *,
        source_warehouse_id: WarehouseIdVO,
        destination_warehouse_id: WarehouseIdVO,
        source_warehouse: WarehouseSnapshot,
        destination_warehouse: WarehouseSnapshot,
        lines: tuple[TransferLine, ...],
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
    ) -> None:
        """Требует непустой план, уникальные ID строк и ровно участвующие актуальные снимки товаров."""
        StockTransferConfirmationPolicy.ensure_warehouses(
            source_warehouse_id=source_warehouse_id,
            destination_warehouse_id=destination_warehouse_id,
            source_warehouse=source_warehouse,
            destination_warehouse=destination_warehouse,
        )
        if not isinstance(lines, tuple):
            raise InvalidStockTransferLineError(
                "План передаётся в tuple строк перемещения."
            )
        if not lines:
            raise EmptyStockTransferError("Нельзя подтвердить перемещение без строк.")
        if not isinstance(inventory_items, tuple):
            raise InvalidStockTransferContextError(
                "Нужен tuple учётных снимков участвующих товаров."
            )
        by_item = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemStockSnapshot):
                raise InvalidInventoryItemStockSnapshotError(
                    "Нужны учётные снимки товаров перемещения."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InvalidStockTransferContextError(
                    "Снимок каждого товара передаётся только один раз."
                )
            by_item[item.inventory_item_id] = item
        ids, items = set(), set()
        for line in lines:
            if not isinstance(line, TransferLine):
                raise InvalidStockTransferLineError(
                    "Состав перемещения содержит только TransferLine."
                )
            line.ensure_valid()
            if line.id in ids:
                raise StockTransferLineConflictError(
                    "ID строки перемещения не должен повторяться."
                )
            ids.add(line.id)
            items.add(line.inventory_item_id)
            item = by_item.get(line.inventory_item_id)
            if item is None:
                raise InvalidStockTransferContextError(
                    "Отсутствует учётный снимок товара одной из строк."
                )
            line.ensure_compatible(inventory_item=item)
        if items != set(by_item):
            raise InvalidStockTransferContextError(
                "Лишние снимки товаров перемещения не допускаются."
            )
