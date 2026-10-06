from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.catalog.domain.product.value_object.kind import ProductKind


@dataclass(frozen=True, slots=True)
class ProductListItemDTO:
    id: UUID
    kind: ProductKind
    name: str | None
    variant_count: int
    primary_category_id: UUID | None
    primary_category_name: str | None
    updated_at: datetime
