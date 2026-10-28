from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery


from src.modules.catalog.application.catalog_item.command.update_catalog_item.command import (
    UpdateCatalogItemContent,
)


@dataclass(frozen=True, slots=True)
class UpdateCatalogVariantCommand:
    """Типизированное намерение изменить только явно переданные поля товара."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    variant_id: CatalogItemIdVO
    fields: frozenset[str]
    locale: str | None = None
    status: CatalogItemStatus | None = None
    sku: SkuCodeVO | None = None
    virtual: bool | None = None
    price_specification: PriceSpecificationVO | None = None
    stock: StockSpecificationVO | None = None
    weight: WeightVO | None = None
    dimensions: DimensionsVO | None = None
    content: UpdateCatalogItemContent | None = None
    gallery: CatalogItemGallery | None = None
