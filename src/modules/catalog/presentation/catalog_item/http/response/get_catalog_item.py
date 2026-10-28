from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Literal
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    PriceValue,
    StockValue,
    WeightValue,
    DimensionsValue,
    GalleryValue,
)


class CatalogItemSourcesResponse(BaseModel):
    """Идентичности владельцев эффективных разделов выбранной locale."""

    title: UUID | None
    body: UUID | None
    gallery: UUID | None
    weight: UUID | None
    dimensions: UUID | None
    stock: UUID


class CatalogItemDetailsResponse(BaseModel):
    """Поля и вычисляемые значения самостоятельного товара выбранной locale."""

    id: UUID
    product_type_id: UUID
    status: Literal["draft", "active", "archived"]
    sku: str | None
    virtual: bool
    price_specification: PriceValue | None
    price: Decimal | None
    weight: WeightValue | None
    dimensions: DimensionsValue | None
    stock: StockValue
    stock_status: str
    backorders_allowed: bool
    backordered: bool
    available_for_sale: bool
    available_for_publication: bool
    content: dict[str, str] | None
    gallery: GalleryValue | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    kind: Literal["simple", "variable", "variant"] = "simple"
    parent_id: UUID | None = None
    stock_source: Literal["own", "parent"] = "own"
    variant_count: int = 0
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    currency: str | None = None
    mixed_currencies: bool = False
    effective_content: dict[str, str] | None = None
    effective_gallery: GalleryValue | None = None
    effective_stock: StockValue | None = None
    effective_weight: WeightValue | None = None
    effective_dimensions: DimensionsValue | None = None
    sources: CatalogItemSourcesResponse | None = None


class GetCatalogItemResponse(BaseModel):
    """HTTP-результат сценария чтения карточки товара."""

    item: CatalogItemDetailsResponse
    as_of: datetime
