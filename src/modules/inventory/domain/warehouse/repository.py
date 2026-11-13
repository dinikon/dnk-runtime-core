from typing import Protocol

from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class WarehouseRepositoryProtocol(Protocol):
    """Определяет запись склада в общей tenant-транзакции."""

    async def get_for_share(self, identifier: WarehouseIdVO) -> Warehouse | None:
        """Читает актуальный склад с совместимой блокировкой против его изменения."""
        ...

    async def get_for_update(self, identifier: WarehouseIdVO) -> Warehouse | None:
        """Блокирует и восстанавливает актуальную карточку либо возвращает None."""
        ...

    async def add(self, warehouse: Warehouse) -> None:
        """Сохраняет новую карточку без самостоятельного commit."""
        ...

    async def save(self, warehouse: Warehouse) -> None:
        """Сохраняет состояние существующей карточки по ID без upsert."""
        ...
