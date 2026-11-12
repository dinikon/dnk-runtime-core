from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from typing import Protocol

from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class InventoryItemRepositoryProtocol(Protocol):
    """Определяет запись позиции в tenant-контексте внешнего UoW."""

    async def add(self, item: InventoryItem) -> None:
        """Добавляет агрегат или сообщает о занятом SKU/штрихкоде, без commit."""
        ...

    async def add_if_absent(self, item: InventoryItem) -> bool:
        """Добавляет агрегат, если SKU свободен; конкурентный дубль не прерывает UoW."""
        ...

    async def get_by_sku_for_update(self, sku: SkuVO) -> InventoryItem | None:
        """Блокирует и восстанавливает точное каноническое совпадение."""
        ...

    async def get_for_update(
        self, identifier: InventoryItemIdVO
    ) -> InventoryItem | None:
        """Блокирует корень и восстанавливает весь сохранённый агрегат либо возвращает None."""
        ...

    async def save(self, item: InventoryItem) -> None:
        """Сохраняет состояние и состав атомарно без самостоятельного commit."""
        ...

    async def delete(self, item: InventoryItem) -> None:
        """Удаляет корень и принадлежащие ему штрихкоды без самостоятельного commit."""
        ...
