from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    DimensionsVO,
)
from dataclasses import dataclass
from uuid import UUID
from decimal import Decimal
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)


@dataclass(frozen=True, slots=True)
class CatalogItemListImageDTO:
    """Главное изображение компактной строки списка."""

    id: UUID
    file_id: UUID
    position: int
    alt: str
    caption: str


@dataclass(frozen=True, slots=True)
class CatalogItemListRowDTO:
    """Компактная строка списка без полных данных редактора."""

    id: UUID

    status: CatalogItemStatus
    sku: str | None
    title: str | None
    price: Decimal | None
    currency: str | None
    stock_status: str | None
    primary_image: CatalogItemListImageDTO | None
    available_for_sale: bool
    weight: WeightVO | None
    dimensions: DimensionsVO | None
    kind: str = "simple"
    parent_id: UUID | None = None
    variant_count: int = 0
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    mixed_currencies: bool = False
    manage_stock: bool = False
    stock_quantity: int | None = None
    stock_source: str = "own"
