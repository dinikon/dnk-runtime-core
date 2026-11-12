from dataclasses import dataclass

from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class GetWarehouseQuery:
    """Передаёт ID карточки склада текущего tenant."""

    warehouse_id: WarehouseIdVO
