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
class CatalogItemPublicationImageDTO:
    """Назначение изображения в результате чтения."""

    id: UUID
    file_id: UUID
    position: int
    alt: str
    caption: str


@dataclass(frozen=True, slots=True)
class CatalogItemPublicationGalleryDTO:
    """Локализованная галерея результата чтения."""

    images: tuple[CatalogItemPublicationImageDTO, ...]
    primary_image_id: UUID | None


@dataclass(frozen=True, slots=True)
class CatalogItemPublicationAttributeDTO:
    """Характеристика результата чтения."""

    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    visible: bool
    position: int


@dataclass(frozen=True, slots=True)
class CatalogItemPublicationMetadataDTO:
    """Типизированное дополнительное значение результата чтения."""

    key: str
    value_type: str
    value: str | Decimal | bool
    position: int


@dataclass(frozen=True, slots=True)
class CatalogItemPublicationDTO:
    """Проекция самостоятельного товара для сценария get_catalog_items_publication_snapshot."""

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
    gallery: CatalogItemPublicationGalleryDTO | None
    attributes: tuple[CatalogItemPublicationAttributeDTO, ...]
    metadata: tuple[CatalogItemPublicationMetadataDTO, ...]
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
    tag_ids: tuple[UUID, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
)


@dataclass(frozen=True, slots=True)
class GetCatalogItemsPublicationSnapshotResultDTO:
    """Согласованный batch-снимок простых товаров для потребителей Catalog."""

    items: tuple[CatalogItemPublicationDTO, ...]
    schema: ProductTypeSchemaSnapshot
    locale: str
    as_of: datetime
