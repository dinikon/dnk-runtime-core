from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    WeightVO,
)


@dataclass(frozen=True, slots=True)
class SetCatalogItemMeasurementsCommand:
    """Явный вход сценария set_catalog_item_measurements в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_root_revision: int
    weight: WeightVO | None
    dimensions: DimensionsVO | None
