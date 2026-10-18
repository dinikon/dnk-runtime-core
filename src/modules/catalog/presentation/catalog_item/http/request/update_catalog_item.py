from typing import Self
from pydantic import (
    BaseModel,
    ConfigDict,
    StrictBool,
    Field,
    field_validator,
    model_validator,
)
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


class UpdateCatalogItemContentRequest(BaseModel):
    """Полный перевод выбранной locale и версия его схемы."""

    model_config = ConfigDict(extra="forbid")
    expected_schema_version: int = Field(ge=1)
    values: dict[str, str]


class UpdateCatalogItemRequest(BaseModel):
    """Частичное изменение товара: отсутствие поля отличается от явного null."""

    model_config = ConfigDict(extra="forbid")
    status: CatalogItemStatus | None = None
    sku: str | None = None
    virtual: StrictBool | None = None
    price_specification: PriceValue | None = None
    stock: StockValue | None = None
    weight: WeightValue | None = None
    dimensions: DimensionsValue | None = None
    content: UpdateCatalogItemContentRequest | None = None
    gallery: GalleryValue | None = None

    @field_validator("status", "virtual", "stock")
    @classmethod
    def reject_null(cls, value: object) -> object:
        """Отклоняет явный null обязательных значений, сохраняя пропущенные поля."""
        if value is None:
            raise ValueError("Значение не может быть null.")
        return value

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Запрещает PATCH без изменения бизнес-полей."""
        if not self.model_fields_set:
            raise ValueError("Нужен хотя бы один изменяемый раздел.")
        return self
