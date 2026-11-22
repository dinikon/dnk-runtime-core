from src.modules.catalog.domain.catalog_item.value_object.categories import (
    CatalogItemCategoriesVO,
)
from dataclasses import dataclass, field
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
from src.modules.catalog.domain.catalog_item.value_object.purchase_price import (
    PurchasePriceVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery


@dataclass(frozen=True, slots=True)
class UpdateCatalogItemContent:
    """Полный перевод и ожидаемая версия фиксированной схемы."""

    expected_schema_version: int
    values: dict[str, str]


@dataclass(frozen=True, slots=True)
class UpdateCatalogItemCommand:
    """Типизированное намерение изменить только явно переданные поля товара."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    item_id: CatalogItemIdVO
    fields: frozenset[str]
    locale: str | None = None
    status: CatalogItemStatus | None = None
    sku: SkuCodeVO | None = None
    virtual: bool | None = None
    price_specification: PriceSpecificationVO | None = None
    change_primary_only: bool = field(default=False, kw_only=True)
    categories: CatalogItemCategoriesVO | None = field(default=None, kw_only=True)
    purchase_price: PurchasePriceVO | None = field(default=None, kw_only=True)
    stock: StockSpecificationVO | None = None
    weight: WeightVO | None = None
    dimensions: DimensionsVO | None = None
    content: UpdateCatalogItemContent | None = None
    gallery: CatalogItemGallery | None = None
