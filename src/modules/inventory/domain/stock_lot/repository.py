from typing import Protocol

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO


class StockLotRepositoryProtocol(Protocol):
    """Определяет сохранение самостоятельной партии в общей tenant-транзакции."""

    async def add(self, lot: StockLot) -> None:
        """Добавляет партию без commit или сообщает о занятом номере внутри SKU."""
        ...

    async def get_for_update(
        self, identifier: StockLotIdVO, *, inventory_item_id: InventoryItemIdVO
    ) -> StockLot | None:
        """Блокирует и перечитывает партию только внутри указанного владельца."""
        ...

    async def save(self, lot: StockLot) -> None:
        """Сохраняет даты существующей партии без изменения номера/владельца и без commit."""
        ...
