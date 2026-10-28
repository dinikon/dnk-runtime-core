from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)


@dataclass(frozen=True, slots=True)
class CatalogItemDetailsImageDTO:
    """Назначение изображения в результате чтения."""

    id: UUID
    file_id: UUID
    position: int
    alt: str
    caption: str


@dataclass(frozen=True, slots=True)
class CatalogItemDetailsGalleryDTO:
    """Локализованная галерея результата чтения."""

    images: tuple[CatalogItemDetailsImageDTO, ...]
    primary_image_id: UUID | None


@dataclass(frozen=True, slots=True)
class CatalogItemSourcesDTO:
    """Владельцы эффективных разделов выбранной locale."""

    title: UUID | None
    body: UUID | None
    gallery: UUID | None
    weight: UUID | None
    dimensions: UUID | None
    stock: UUID


@dataclass(frozen=True, slots=True)
class CatalogItemDetailsDTO:
    """Проекция самостоятельного товара для сценария get_catalog_item."""

    id: UUID
    product_type_id: UUID
    status: CatalogItemStatus
    sku: str | None
    virtual: bool
    price_specification: PriceSpecificationVO | None
    price: Decimal | None
    weight: WeightVO | None
    dimensions: DimensionsVO | None
    stock: StockSpecificationVO
    stock_status: str
    backorders_allowed: bool
    backordered: bool
    available_for_sale: bool
    available_for_publication: bool
    content: dict[str, str] | None
    gallery: CatalogItemDetailsGalleryDTO | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    kind: str = "simple"
    parent_id: UUID | None = None
    stock_source: str = "own"
    variant_count: int = 0
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    currency: str | None = None
    mixed_currencies: bool = False
    effective_content: dict[str, str] | None = None
    effective_gallery: CatalogItemDetailsGalleryDTO | None = None
    effective_stock: StockSpecificationVO | None = None
    effective_weight: WeightVO | None = None
    effective_dimensions: DimensionsVO | None = None
    sources: CatalogItemSourcesDTO | None = None


@dataclass(frozen=True, slots=True)
class GetCatalogItemResultDTO:
    """Детали товара выбранной locale на согласованный момент."""

    item: CatalogItemDetailsDTO
    as_of: datetime
