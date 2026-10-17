from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
    WeightVO,
    WeightUnit,
    LengthVO,
    LengthUnit,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)


class PriceValue(BaseModel):
    """Каноническая спецификация цены, без вычисляемого price."""

    model_config = ConfigDict(extra="forbid")
    regular_price: Decimal
    currency: str
    sale_price: Decimal | None = None
    date_on_sale_from: datetime | None = None
    date_on_sale_to: datetime | None = None

    def to_vo(self) -> PriceSpecificationVO:
        """Сохраняет Decimal и явные границы интервала."""
        return PriceSpecificationVO(
            self.regular_price,
            self.currency,
            self.sale_price,
            self.date_on_sale_from,
            self.date_on_sale_to,
        )


class WeightValue(BaseModel):
    """Масса с собственной единицей измерения."""

    model_config = ConfigDict(extra="forbid")
    value: Decimal
    unit: Literal["g", "kg"]

    def to_vo(self) -> WeightVO:
        """Передаёт массу и её единицу без округления."""
        return WeightVO(self.value, WeightUnit(self.unit))


class LengthValue(BaseModel):
    """Один линейный размер с собственной единицей."""

    model_config = ConfigDict(extra="forbid")
    value: Decimal
    unit: Literal["cm", "m"]

    def to_vo(self) -> LengthVO:
        """Передаёт размер и его единицу без округления."""
        return LengthVO(self.value, LengthUnit(self.unit))


class DimensionsValue(BaseModel):
    """Полный раздел независимо необязательных измерений."""

    model_config = ConfigDict(extra="forbid")
    length: LengthValue | None
    width: LengthValue | None
    height: LengthValue | None

    def to_vo(self) -> DimensionsVO:
        """Преобразует каждый компонент вместе с его собственной единицей."""
        return DimensionsVO(
            self.length.to_vo() if self.length is not None else None,
            self.width.to_vo() if self.width is not None else None,
            self.height.to_vo() if self.height is not None else None,
        )


class StockValue(BaseModel):
    """Собственный boolean учёта и согласованные настройки наличия."""

    model_config = ConfigDict(extra="forbid")
    manage_stock: StrictBool
    stock_quantity: StrictInt | None
    stock_status: Literal["in_stock", "out_of_stock", "on_backorder"] | None
    backorders: Literal["no", "notify", "yes"]

    def to_vo(self) -> StockSpecificationVO:
        """Передаёт проверку сочетаний доменному VO."""
        return StockSpecificationVO(
            self.manage_stock,
            self.stock_quantity,
            StockStatus(self.stock_status) if self.stock_status else None,
            BackorderPolicy(self.backorders),
        )


class AttributeValue(BaseModel):
    """Enum-характеристика самостоятельного товара."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    visible: bool = True
    position: int = Field(ge=0)

    def to_vo(self) -> EnumAttributeAssignmentVO:
        """Создаёт назначение для проверки в агрегате."""
        return EnumAttributeAssignmentVO(
            AttributeIdVO(self.attribute_id),
            tuple(AttributeOptionIdVO(i) for i in self.option_ids),
            self.visible,
            self.position,
        )


class MetadataValue(BaseModel):
    """Типизированное расширение без platform payload."""

    model_config = ConfigDict(extra="forbid")
    key: str
    value_type: Literal["text", "decimal", "boolean"]
    value: str | Decimal | StrictBool
    position: int = Field(ge=0)

    def to_entity(self) -> CatalogMetadataEntry:
        """Преобразует числовую строку в Decimal только при явном типе."""
        value = (
            Decimal(self.value)
            if self.value_type == "decimal" and self.value is not None
            else self.value
        )
        return CatalogMetadataEntry.create(
            self.key, self.value_type, value, self.position
        )


class ImageValue(BaseModel):
    """Локализованное назначение готового Files файла."""

    model_config = ConfigDict(extra="forbid")
    id: UUID
    file_id: UUID
    position: int = Field(ge=0)
    alt: str = ""
    caption: str = ""


class GalleryValue(BaseModel):
    """Полная локализованная галерея самостоятельного товара."""

    model_config = ConfigDict(extra="forbid")
    images: tuple[ImageValue, ...] = ()
    primary_image_id: UUID | None = None

    def to_entity(self) -> CatalogItemGallery:
        """Передаёт проверку ownership и primary агрегату."""
        return CatalogItemGallery.create(
            tuple(
                CatalogItemImage.create(
                    EntityIdVO(i.id),
                    EntityIdVO(i.file_id),
                    i.position,
                    i.alt,
                    i.caption,
                )
                for i in self.images
            ),
            EntityIdVO(self.primary_image_id) if self.primary_image_id else None,
        )


class BlockSchemaResponse(BaseModel):
    """Фиксированное определение блока контента."""

    id: UUID
    code: str
    value_type: str
    required: bool
    position: int
    label: str | None


class SchemaResponse(BaseModel):
    """Версия системной схемы Default."""

    id: UUID
    code: str
    schema_version: int
    blocks: tuple[BlockSchemaResponse, ...]
    label: str | None


class ListItemResponse(BaseModel):
    """Краткие поля списка товаров без собственного контента и внутренних связей."""

    id: UUID
    revision: int
    status: Literal["draft", "active", "archived"]
    sku: str | None
    title: str | None
    price: Decimal | None
    currency: str | None
    stock_status: str | None
    primary_image: ImageValue | None
    available_for_sale: bool
    weight: WeightValue | None
    dimensions: DimensionsValue | None
