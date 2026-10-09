from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product_type.value_object.block_link import (
    ProductTypeContentBlock,
)


@dataclass(frozen=True, slots=True)
class CreateProductTypeCommand:
    """Вход сценария create_product_type; контекст получен от доверенной границы."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    code: str
    locale: str
    label: str
    blocks: tuple[ProductTypeContentBlock, ...]
