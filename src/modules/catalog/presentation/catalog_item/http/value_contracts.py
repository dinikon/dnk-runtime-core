from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Generic, TypeVar, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideVO,
    OverrideMode,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockManagement,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.axis import VariationAxis
from src.modules.catalog.domain.catalog_item.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.application.catalog_item.structure_input import (
    VariantStructureInput,
    VariableStructureInput,
)

T = TypeVar("T")


class ValueOverride(BaseModel, Generic[T]):
    """Transport компонент явного inherit/set/clear."""

    model_config = ConfigDict(extra="forbid")
    mode: Literal["inherit", "set", "clear"]
    value: T | None = None

    def to_vo(self) -> OverrideVO[T]:
        """Преобразует транспортный режим в проверяемый VO."""
        return OverrideVO(OverrideMode(self.mode), self.value)


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


class DimensionsValue(BaseModel):
    """Полная группа измерений в миллиметрах."""

    model_config = ConfigDict(extra="forbid")
    length: Decimal
    width: Decimal
    height: Decimal

    def to_vo(self) -> DimensionsVO:
        """Преобразует все три измерения одной группой."""
        return DimensionsVO(self.length, self.width, self.height)


class StockValue(BaseModel):
    """Собственное, заявленное или общее наличие."""

    model_config = ConfigDict(extra="forbid")
    manage_stock: Literal["none", "own", "parent"]
    stock_quantity: int | None = None
    stock_status: Literal["in_stock", "out_of_stock", "on_backorder"] | None = None
    backorders: Literal["no", "notify", "yes"] | None = None

    def to_vo(self) -> StockSpecificationVO:
        """Передаёт проверку сочетаний доменному VO."""
        return StockSpecificationVO(
            StockManagement(self.manage_stock),
            self.stock_quantity,
            StockStatus(self.stock_status) if self.stock_status else None,
            BackorderPolicy(self.backorders) if self.backorders else None,
        )


class SelectionValue(BaseModel):
    """Одна пара устойчивых ID оси и enum option."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_id: UUID


class AxisValue(BaseModel):
    """Ось вариации с независимой видимостью."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    position: int = Field(ge=0)
    visible: bool = True

    def to_vo(self) -> VariationAxis:
        """Преобразует устойчивые ссылки без поиска по labels."""
        return VariationAxis(
            AttributeIdVO(self.attribute_id),
            tuple(AttributeOptionIdVO(i) for i in self.option_ids),
            self.position,
            self.visible,
        )


class VariantStructureValue(BaseModel):
    """Существующий ребёнок либо запрос создания нового."""

    model_config = ConfigDict(extra="forbid")
    item_id: UUID | None = None
    selection: tuple[SelectionValue, ...]


class StructureValue(BaseModel):
    """Полная заменяемая структура одного уровня."""

    model_config = ConfigDict(extra="forbid")
    axes: tuple[AxisValue, ...]
    variants: tuple[VariantStructureValue, ...]
    default_selection: tuple[SelectionValue, ...] | None = None

    def to_input(self) -> VariableStructureInput:
        """Создаёт вход структурного сценария без мутации Domain."""
        variants = tuple(
            VariantStructureInput(
                CatalogItemIdVO(v.item_id) if v.item_id else None,
                VariationSelectionVO(
                    tuple(
                        (
                            AttributeIdVO(s.attribute_id),
                            AttributeOptionIdVO(s.option_id),
                        )
                        for s in v.selection
                    )
                ),
            )
            for v in self.variants
        )
        default = (
            VariationSelectionVO(
                tuple(
                    (AttributeIdVO(s.attribute_id), AttributeOptionIdVO(s.option_id))
                    for s in self.default_selection
                )
            )
            if self.default_selection is not None
            else None
        )
        return VariableStructureInput(
            tuple(a.to_vo() for a in self.axes), variants, default
        )


class AttributeValue(BaseModel):
    """Own enum назначение; отсутствие означает наследование."""

    model_config = ConfigDict(extra="forbid")
    attribute_id: UUID
    option_ids: tuple[UUID, ...] = ()
    visible: bool = True
    position: int = Field(ge=0)
    mode: Literal["set", "clear"] = "set"

    def to_vo(self) -> EnumAttributeAssignmentVO:
        """Создаёт назначение для проверки в агрегате."""
        return EnumAttributeAssignmentVO(
            AttributeIdVO(self.attribute_id),
            tuple(AttributeOptionIdVO(i) for i in self.option_ids),
            self.visible,
            self.position,
            OverrideMode(self.mode),
        )


class MetadataValue(BaseModel):
    """Типизированное расширение без platform payload."""

    model_config = ConfigDict(extra="forbid")
    key: str
    value_type: Literal["text", "decimal", "boolean"] | None = None
    value: str | Decimal | StrictBool | None = None
    position: int = Field(ge=0)
    mode: Literal["set", "clear"] = "set"

    def to_entity(self) -> CatalogMetadataEntry:
        """Преобразует числовую строку в Decimal только при явном типе."""
        value = (
            Decimal(self.value)
            if self.value_type == "decimal" and self.value is not None
            else self.value
        )
        return CatalogMetadataEntry.create(
            self.key, self.value_type, value, self.position, OverrideMode(self.mode)
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
    """Полная галерея; пустая suppresses наследование."""

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


class SelectionResponse(BaseModel):
    """Канонический выбор по парам UUID."""

    values: tuple[tuple[UUID, UUID], ...]


class OriginResponse(BaseModel):
    """Источник effective значения для объяснения наследования."""

    source: str
    item_id: UUID | None
    locale: str | None = None


class OwnItemResponse(BaseModel):
    """Own поля конкретного узла единой модели."""

    id: UUID
    kind: Literal["simple", "variable", "variant"]
    parent_id: UUID | None
    product_type_id: UUID | None
    status: Literal["draft", "active", "archived"]
    sku: str | None
    virtual: ValueOverride[bool]
    price: ValueOverride[PriceValue]
    weight: ValueOverride[Decimal]
    dimensions: ValueOverride[DimensionsValue]
    stock: StockValue | None
    translations: dict[str, dict[str, ValueOverride[str]]]
    galleries: dict[str, GalleryValue]
    attributes: tuple[AttributeValue, ...]
    metadata: tuple[MetadataValue, ...]
    selection: SelectionResponse
    axes: tuple[AxisValue, ...]
    default_selection: SelectionResponse | None
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
    tag_ids: tuple[UUID, ...]
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


class EffectiveItemResponse(BaseModel):
    """Разрешённые значения и origin, без сохранения вычислений в SQL."""

    content: dict[str, str] | None
    virtual: bool
    price_specification: PriceValue | None
    price: Decimal | None
    weight: Decimal | None
    dimensions: DimensionsValue | None
    stock: StockValue | None
    stock_source_id: UUID | None
    gallery: GalleryValue | None
    attributes: tuple[AttributeValue, ...]
    metadata: tuple[MetadataValue, ...]
    available_for_publication: bool
    origins: dict[str, OriginResponse]


class ReadItemResponse(BaseModel):
    """Общий вложенный компонент разных read контрактов."""

    root_id: UUID
    root_revision: int
    own: OwnItemResponse
    effective: EffectiveItemResponse
    stock_status: str | None
    backorders_allowed: bool | None
    backordered: bool | None
    price_min: Decimal | None
    price_max: Decimal | None
    price_incomplete: bool
    price_currency: str | None


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
    kind: Literal["simple", "variable", "variant"]
    root_id: UUID
    root_revision: int
    revision: int
    status: Literal["draft", "active", "archived"]
    sku: str | None
    title: str | None
    price: Decimal | None
    currency: str | None
    price_min: Decimal | None
    price_max: Decimal | None
    price_incomplete: bool
    stock_status: str | None
    primary_image: ImageValue | None
