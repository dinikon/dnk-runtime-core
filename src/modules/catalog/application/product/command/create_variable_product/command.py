from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.application.product.structure_input import (
    VariableStructureInput,
)


@dataclass(frozen=True, slots=True)
class CreateVariableProductCommand:
    """Вход сценария create_variable_product с полной целевой структурой."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    structure: VariableStructureInput
    product_type_id: ProductTypeIdVO | None = None
