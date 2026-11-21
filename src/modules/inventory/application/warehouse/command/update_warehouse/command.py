from dataclasses import dataclass

from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class UpdateWarehouseCommand:
    """Передаёт ID и явно изменяемые поля без подстановки defaults создания."""

    warehouse_id: WarehouseIdVO
    fields: frozenset[str]
    code: str | None = None
    name: str | None = None
    is_active: bool | None = None
