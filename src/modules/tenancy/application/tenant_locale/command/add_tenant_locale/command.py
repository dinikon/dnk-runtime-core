from dataclasses import dataclass

from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class AddTenantLocaleCommand:
    """Выбор системной локали текущим tenant."""

    code: str
    actor_id: EntityIdVO
