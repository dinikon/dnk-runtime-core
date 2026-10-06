from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.domain.product.value_object.kind import ProductKind


@dataclass(frozen=True, slots=True)
class PutVariantStructureResultDTO:
    product_id: UUID
    kind: ProductKind
    variant_ids: tuple[UUID, ...]
