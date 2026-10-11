from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.application.catalog_item.structure_input import (
    VariableStructureInput,
)


@dataclass(frozen=True, slots=True)
class ReplaceCatalogItemStructureCommand:
    """Явный вход сценария replace_catalog_item_structure в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_root_revision: int
    structure: VariableStructureInput
    removed_ids: frozenset[CatalogItemIdVO]
