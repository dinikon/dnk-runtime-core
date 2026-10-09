from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateWarehouseCommand:
    """Создание склада с доверенными tenant/actor и явно заданными настройками."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    code: str
    title: str
    warehouse_type: str
    timezone: str
