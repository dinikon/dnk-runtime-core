from typing import Protocol

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.domain.warehouse.aggregate import Warehouse
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)


class WarehouseRepositoryProtocol(Protocol):
    """Хранение агрегатов в tenant-сессии общей внешней транзакции."""

    async def add(self, *, tenant_id: EntityIdVO, warehouse: Warehouse) -> None:
        """Добавляет агрегат без commit; занятый код вызывает доменную ошибку."""
        ...

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        warehouse_id: WarehouseIdVO,
    ) -> Warehouse | None:
        """Восстанавливает агрегат текущего tenant либо возвращает None."""
        ...
