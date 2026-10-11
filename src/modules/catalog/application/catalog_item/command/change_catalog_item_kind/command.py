from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.application.catalog_item.structure_input import (
    VariableStructureInput,
)


@dataclass(frozen=True, slots=True)
class ChangeCatalogItemKindCommand:
    """Явный вход сценария change_catalog_item_kind в доверенном tenant-контексте."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    expected_root_revision: int
    kind: CatalogItemKind
    structure: VariableStructureInput | None
    selected_item_id: CatalogItemIdVO | None
    discarded_ids: frozenset[CatalogItemIdVO]
    carry_to_index: int | None
