from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
)
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogVariantValues,
    CreateCatalogItemTranslation,
)
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


class CreateCatalogVariantTranslationRequest(BaseModel):
    """Принимает полный контент одной локали с версией схемы."""

    model_config = ConfigDict(extra="forbid")
    expected_schema_version: int = Field(ge=1)
    values: dict[str, str]


class CreateCatalogVariantRequest(BaseModel):
    """Собственные начальные поля новой позиции указанного родителя."""

    model_config = ConfigDict(extra="forbid")
    status: CatalogItemStatus = CatalogItemStatus.DRAFT
    sku: str | None = None
    virtual: StrictBool = False
    price_specification: PriceValue | None = None
    stock: StockValue | None = None
    weight: WeightValue | None = None
    dimensions: DimensionsValue | None = None
    translations: dict[str, CreateCatalogVariantTranslationRequest] = Field(
        default_factory=dict
    )
    galleries: dict[str, GalleryValue] = Field(default_factory=dict)

    @field_validator("stock")
    @classmethod
    def reject_null_stock(cls, value: StockValue | None) -> StockValue:
        """Отклоняет очистку обязательных собственных настроек."""
        if value is None:
            raise ValueError("Настройки наличия не могут быть null.")
        return value

    def to_values(self) -> CreateCatalogVariantValues:
        """Преобразует собственные значения без разрешения наследования."""
        return CreateCatalogVariantValues(
            status=self.status,
            sku=self.sku,
            virtual=self.virtual,
            price_specification=(
                self.price_specification.to_vo() if self.price_specification else None
            ),
            stock=self.stock.to_vo() if self.stock else StockSpecificationVO(),
            weight=self.weight.to_vo() if self.weight else None,
            dimensions=self.dimensions.to_vo() if self.dimensions else None,
            translations={
                k: CreateCatalogItemTranslation(v.values, v.expected_schema_version)
                for k, v in self.translations.items()
            },
            galleries={k: v.to_entity() for k, v in self.galleries.items()},
        )
