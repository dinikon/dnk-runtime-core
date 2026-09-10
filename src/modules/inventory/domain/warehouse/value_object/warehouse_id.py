from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class WarehouseIdVO(EntityIdVO):
    """Типизированный идентификатор склада."""
