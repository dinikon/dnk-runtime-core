from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateCatalogItemCommand:
    """Вход создания самостоятельного корня simple."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    virtual: bool = False
