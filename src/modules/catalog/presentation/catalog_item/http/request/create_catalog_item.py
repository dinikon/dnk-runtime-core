from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    PriceValue,
    StockValue,
    WeightValue,
    DimensionsValue,
    GalleryValue,
)


class CreateCatalogItemTranslationRequest(BaseModel):
    """Принимает полный контент одной локали с версией схемы."""

    model_config = ConfigDict(extra="forbid")
    expected_schema_version: int = Field(ge=1)
    values: dict[str, str]


class CreateCatalogItemRequest(BaseModel):
    """Создаёт пустой или заполненный товар; отсутствующие разделы получают defaults."""

    model_config = ConfigDict(extra="forbid")
    product_type_code: str = "default"
    virtual: StrictBool = False
    status: CatalogItemStatus = CatalogItemStatus.DRAFT
    sku: str | None = None
    price_specification: PriceValue | None = None
    stock: StockValue | None = None
    weight: WeightValue | None = None
    dimensions: DimensionsValue | None = None
    translations: dict[str, CreateCatalogItemTranslationRequest] = Field(
        default_factory=dict
    )
    galleries: dict[str, GalleryValue] = Field(default_factory=dict)

    @field_validator("stock")
    @classmethod
    def reject_null_stock(cls, value: StockValue | None) -> StockValue:
        """Отличает пропущенный stock с defaults от явно некорректного null."""
        if value is None:
            raise ValueError("Настройки наличия не могут быть null.")
        return value
