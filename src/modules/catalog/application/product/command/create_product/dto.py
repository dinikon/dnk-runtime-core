from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.catalog.domain.product.value_object.kind import ProductKind

@dataclass(frozen=True, slots=True)
class CreateProductResultDTO:
    id: UUID
    kind: ProductKind
    variant_id: UUID
    sku_id: UUID
    sku_code: str
    content_locales: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
