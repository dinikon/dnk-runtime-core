from dataclasses import dataclass, field
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
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
    WeightVO,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery


@dataclass(frozen=True, slots=True)
class CreateCatalogItemTranslation:
    """Передаёт контент одной локали и ожидаемую версию её схемы."""

    values: dict[str, str]
    expected_schema_version: int | None = None


@dataclass(frozen=True, slots=True)
class CreateCatalogVariantValues:
    """Собственные значения варианта, отсутствующие разделы наследуются."""

    status: CatalogItemStatus = CatalogItemStatus.DRAFT
    sku: str | None = None
    virtual: bool = False
    price_specification: PriceSpecificationVO | None = None
    stock: StockSpecificationVO = field(default_factory=StockSpecificationVO)
    weight: WeightVO | None = None
    dimensions: DimensionsVO | None = None
    translations: dict[str, CreateCatalogItemTranslation] = field(default_factory=dict)
    galleries: dict[str, CatalogItemGallery] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreateCatalogItemValues:
    """Описывает исходные значения самостоятельного товара без внешнего источника."""

    product_type_code: str = "default"
    virtual: bool = False
    status: CatalogItemStatus = CatalogItemStatus.DRAFT
    sku: str | None = None
    price_specification: PriceSpecificationVO | None = None
    stock: StockSpecificationVO = field(default_factory=StockSpecificationVO)
    weight: WeightVO | None = None
    dimensions: DimensionsVO | None = None
    translations: dict[str, CreateCatalogItemTranslation] = field(default_factory=dict)
    galleries: dict[str, CatalogItemGallery] = field(default_factory=dict)
    kind: CatalogItemKind = CatalogItemKind.SIMPLE
    variants: tuple[CreateCatalogVariantValues, ...] = ()
