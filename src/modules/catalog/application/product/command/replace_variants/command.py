from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.application.product.structure_input import (
    VariableStructureInput,
)


@dataclass(frozen=True, slots=True)
class ReplaceVariantsCommand:
    """Вход сценария replace_variants с полной целевой структурой."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    structure: VariableStructureInput
