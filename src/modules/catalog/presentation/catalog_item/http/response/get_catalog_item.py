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
    AttributeValue,
    MetadataValue,
)


class CatalogItemDetailsResponse(BaseModel):
    """Поля и вычисляемые значения самостоятельного товара выбранной locale."""

    id: UUID
    revision: int
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
    attributes: tuple[AttributeValue, ...]
    metadata: tuple[MetadataValue, ...]
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
    tag_ids: tuple[UUID, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


class GetCatalogItemResponse(BaseModel):
    """HTTP-результат сценария чтения карточки товара."""

    item: CatalogItemDetailsResponse
    as_of: datetime
