from typing import Protocol

from src.modules.inventory.domain.warehouse.entity import Warehouse
from src.modules.inventory.domain.warehouse.value_object import WarehouseIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class WarehouseRepositoryProtocol(Protocol):
    """Контракт хранения складов с явным tenant scope каждой операции."""

    async def add(self, *, tenant_id: EntityIdVO, warehouse: Warehouse) -> None:
        """Добавляет склад в схему указанного tenant."""
        ...

    async def get_by_id(
        self, *, tenant_id: EntityIdVO, warehouse_id: WarehouseIdVO
    ) -> Warehouse | None:
        """Возвращает склад только из схемы указанного tenant."""
        ...
