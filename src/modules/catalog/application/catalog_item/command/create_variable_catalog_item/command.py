from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.application.catalog_item.structure_input import (
    VariableStructureInput,
)


@dataclass(frozen=True, slots=True)
class CreateVariableCatalogItemCommand:
    """Вход создания самостоятельного корня variable."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    structure: VariableStructureInput
