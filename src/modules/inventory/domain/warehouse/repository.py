from typing import Protocol

from src.modules.inventory.domain.warehouse.aggregate import Warehouse


class WarehouseRepositoryProtocol(Protocol):
    """Определяет запись склада в общей tenant-транзакции."""

    async def add(self, warehouse: Warehouse) -> None:
        """Сохраняет новую карточку без самостоятельного commit."""
        ...

    async def save(self, warehouse: Warehouse) -> None:
        """Сохраняет состояние существующей карточки по ID без upsert."""
        ...
