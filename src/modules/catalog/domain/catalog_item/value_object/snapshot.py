from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
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


@dataclass(frozen=True, slots=True)
class CatalogItemValuesSnapshot:
    """Снимок собственных значений товара для чистых вычислений и восстановления."""

    id: CatalogItemIdVO
    product_type_id: EntityIdVO
    status: CatalogItemStatus
    sku: str | None
    virtual: bool
    price: PriceSpecificationVO | None
    weight: WeightVO | None
    dimensions: DimensionsVO | None
    stock: StockSpecificationVO

    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO
    translations: dict[str, dict[str, str]]
    galleries: dict[str, CatalogItemGallery]
    attributes: tuple[EnumAttributeAssignmentVO, ...]
    metadata: tuple[CatalogMetadataEntry, ...]
    category_ids: tuple[EntityIdVO, ...]
    primary_category_id: EntityIdVO | None
    tag_ids: tuple[EntityIdVO, ...]
