from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)


@dataclass(frozen=True, slots=True)
class GetWarehouseQuery:
    """Параметры чтения карточки склада в доверенном tenant."""

    tenant_id: EntityIdVO
    warehouse_id: WarehouseIdVO
