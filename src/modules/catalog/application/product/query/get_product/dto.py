from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductContentDTO:
    locale: str
    name: str
    description: str | None


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
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


@dataclass(frozen=True, slots=True)
class ProductSelectionDTO:
    attribute_id: UUID
    attribute_code: str
    attribute_name: str | None
    option_id: UUID
    option_code: str
    option_name: str | None


@dataclass(frozen=True, slots=True)
class ProductVariantDTO:
    id: UUID
    sku_id: UUID
    sku_code: str | None
    selections: tuple[ProductSelectionDTO, ...]


@dataclass(frozen=True, slots=True)
class VariableProductDetailsDTO:
    id: UUID
    type: str
    variants: tuple[ProductVariantDTO, ...]
    requested_locale: str
    content_locales: tuple[str, ...]
    content: ProductContentDTO | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
