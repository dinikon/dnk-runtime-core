from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.catalog.domain.product.value_object.kind import ProductKind


@dataclass(frozen=True, slots=True)
class ProductContentDTO:
    locale: str
    blocks: dict[str, str]


@dataclass(frozen=True, slots=True)
class ProductCategoryDTO:
    id: UUID
    name: str | None


@dataclass(frozen=True, slots=True)
class ProductVariantDTO:
    id: UUID
    sku_id: UUID
    sku_code: str | None
    content_locales: tuple[str, ...]
    content: ProductContentDTO | None


@dataclass(frozen=True, slots=True)
class ProductDetailsDTO:
    id: UUID
    kind: ProductKind
    product_type_id: UUID
    schema_version: int
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
    variants: tuple[ProductVariantDTO, ...] = ()
