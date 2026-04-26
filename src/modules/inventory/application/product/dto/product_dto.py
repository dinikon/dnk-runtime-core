from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ProductDTO:
    """DTO товара, возвращаемый use case и query-репозиторием."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    sku: str
    product_name: str
    description: str | None
    category_id: UUID | None
