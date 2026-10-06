from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class VariantStructureItem:
    sku_id: UUID
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PutVariantStructureCommand:
    product_id: ProductIdVO
    actor_id: EntityIdVO
    kind: ProductKind
    variants: tuple[VariantStructureItem, ...]
