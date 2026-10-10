from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.aggregate import ProductKind
from src.modules.catalog.application.product.structure_input import (
    SimpleStructureInput,
    VariableStructureInput,
)


@dataclass(frozen=True, slots=True)
class ChangeProductKindCommand:
    """Вход сценария change_product_kind с полной целевой структурой."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    kind: ProductKind
    structure: SimpleStructureInput | VariableStructureInput
