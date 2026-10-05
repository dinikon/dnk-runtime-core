from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductContentDTO:
    locale: str
    name: str
    description: str | None


@dataclass(frozen=True, slots=True)
class ProductCategoryDTO:
    id: UUID
    name: str | None


@dataclass(frozen=True, slots=True)
class ProductDetailsDTO:
    id: UUID
    type: str
    variant_id: UUID
    sku_id: UUID
    sku_code: str | None
    requested_locale: str
    content_locales: tuple[str, ...]
    content: ProductContentDTO | None
    categories: tuple[ProductCategoryDTO, ...]
    primary_category_id: UUID | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
