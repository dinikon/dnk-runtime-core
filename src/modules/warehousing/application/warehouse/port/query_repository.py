from typing import Protocol

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseDetailsDTO,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.cursor import (
    WarehouseListCursor,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.dto import (
    ListWarehouseItemDTO,
)
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.domain.warehouse.value_object.status import WarehouseStatus
from src.modules.warehousing.domain.warehouse.value_object.warehouse_type import (
    WarehouseTypeVO,
)


class WarehouseQueryRepositoryProtocol(Protocol):
    """Read-side склада: только DTO отдельных сценариев, без Domain restore."""

    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        warehouse_id: WarehouseIdVO,
    ) -> GetWarehouseDetailsDTO | None:
        """Возвращает карточку текущего tenant либо None."""
        ...

    async def list_items(
        self,
        *,
        tenant_id: EntityIdVO,
        status: WarehouseStatus | None,
        warehouse_type: WarehouseTypeVO | None,
        cursor: WarehouseListCursor | None,
        limit: int,
    ) -> tuple[ListWarehouseItemDTO, ...]:
        """Читает ограниченный список проекций после курсора."""
        ...
