from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO


@dataclass(frozen=True, slots=True)
class SetProductTagsCommand:
    """Полная замена tags с проверкой ревизии товара."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    product_id: ProductIdVO
    expected_revision: int
    tag_ids: tuple[TagIdVO, ...]
