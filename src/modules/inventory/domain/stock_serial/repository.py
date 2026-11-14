from typing import Protocol

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.aggregate import StockSerial


class StockSerialRepositoryProtocol(Protocol):
    """Определяет запись самостоятельного экземпляра в общей tenant-транзакции."""

    async def add(self, serial: StockSerial) -> None:
        """Добавляет экземпляр без commit либо сообщает о занятом номере внутри SKU."""
        ...

    async def get_for_update(
        self, identifier: StockSerialIdVO, *, inventory_item_id: InventoryItemIdVO
    ) -> StockSerial | None:
        """Блокирует и перечитывает экземпляр только внутри указанного SKU."""
        ...

    async def save(self, serial: StockSerial) -> None:
        """Сохраняет номер и связь существующего экземпляра без изменения ID/SKU и commit."""
        ...
