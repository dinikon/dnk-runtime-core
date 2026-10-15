from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.override import OverrideVO
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    WeightVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.catalog_item.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.catalog_item.value_object.axis import VariationAxis


@dataclass(frozen=True, slots=True)
class CatalogItemValuesSnapshot:
    """Значения одного узла для чистой политики без восстановления агрегата в query."""

    id: EntityIdVO
    kind: CatalogItemKind
    parent_id: EntityIdVO | None
    product_type_id: EntityIdVO | None
    status: CatalogItemStatus
    sku: str | None
    virtual: bool
    price: PriceSpecificationVO | None
    weight: WeightVO | None
    dimensions: DimensionsVO | None
    stock: StockSpecificationVO
    translations: dict[str, dict[str, OverrideVO[str]]]
    galleries: dict[str, CatalogItemGallery]
    attributes: tuple[EnumAttributeAssignmentVO, ...]
    metadata: tuple[CatalogMetadataEntry, ...]
    selection: VariationSelectionVO
    axes: tuple[VariationAxis, ...]
    default_selection: VariationSelectionVO | None
    category_ids: tuple[EntityIdVO, ...]
    primary_category_id: EntityIdVO | None
    tag_ids: tuple[EntityIdVO, ...]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO


@dataclass(frozen=True, slots=True)
class ValueOrigin:
    """Источник эффективного значения для редакторов и канальных проекций."""

    source: str
    item_id: EntityIdVO | None
    locale: str | None = None


@dataclass(frozen=True, slots=True)
class EffectiveCatalogItemValues:
    """Разрешённые значения одного узла без канальных overrides."""

    content: dict[str, str] | None
    virtual: bool
    price_specification: PriceSpecificationVO | None
    price: Decimal | None
    weight: WeightVO | None
    dimensions: DimensionsVO | None
    stock: StockSpecificationVO
    stock_source_id: EntityIdVO | None
    gallery: CatalogItemGallery | None
    attributes: tuple[EnumAttributeAssignmentVO, ...]
    metadata: tuple[CatalogMetadataEntry, ...]
    available_for_sale: bool
    available_for_publication: bool
    origins: dict[str, ValueOrigin]


@dataclass(frozen=True, slots=True)
class CatalogFamilySummary:
    """Вычисляемые наличие, доступность и диапазон цен активной семьи."""

    stock_status: StockStatus
    available_for_sale: bool
    price_min: Decimal | None
    price_max: Decimal | None
    price_incomplete: bool
    price_currency: str | None
