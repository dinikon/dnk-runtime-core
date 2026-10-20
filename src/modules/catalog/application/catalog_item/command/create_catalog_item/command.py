from dataclasses import dataclass, field
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
)


@dataclass(frozen=True, slots=True)
class CreateCatalogItemCommand:
    """Создаёт самостоятельный товар из типизированного объекта исходных значений."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product: CreateCatalogItemValues = field(default_factory=CreateCatalogItemValues)
