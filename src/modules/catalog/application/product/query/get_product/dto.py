from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProductAxisDetailsDTO:
    """Ось в собственном read-контракте get_product."""

    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    position: int


@dataclass(frozen=True, slots=True)
class ProductVariantDetailsDTO:
    """Позиция внутри результата get_product с собственным и эффективным контентом."""

    id: UUID
    selection: dict[str, str]
    virtual: bool
    downloadable: bool
    content: dict[str, str] | None
    locales: tuple[str, ...]
    effective_title: str | None
    title_source: str | None


@dataclass(frozen=True, slots=True)
class ProductAttributeValueDetailsDTO:
    """Общее enum-значение в конкретной карточке get_product."""

    attribute_id: UUID
    option_id: UUID
    visible: bool
    position: int


@dataclass(frozen=True, slots=True)
class GetProductDetailsDTO:
    """Карточка Product с полной типизированной структурой чтения."""

    id: UUID
    kind: str
    product_type_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    title: str | None
    axes: tuple[ProductAxisDetailsDTO, ...]
    default_selection: dict[str, str] | None
    variants: tuple[ProductVariantDetailsDTO, ...]

    attribute_values: tuple[ProductAttributeValueDetailsDTO, ...]
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
    tag_ids: tuple[UUID, ...]
