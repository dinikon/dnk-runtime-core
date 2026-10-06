from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class PutProductContentCommand:
    product_id: ProductIdVO
    actor_id: EntityIdVO
    locale: str
    schema_version: int
    blocks: dict[str, str]
