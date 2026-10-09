from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product_type.value_object.block_link import (
    ProductTypeContentBlock,
)


@dataclass(frozen=True, slots=True)
class ReplaceProductTypeSchemaCommand:
    """Вход сценария replace_product_type_schema; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_type_id: ProductTypeIdVO
    expected_revision: int
    expected_schema_version: int
    blocks: tuple[ProductTypeContentBlock, ...]
