from pydantic import BaseModel
from uuid import UUID


class GetProductAxisResponse(BaseModel):
    """Ось в собственном read-контракте get_product."""

    attribute_id: UUID
    option_ids: tuple[UUID, ...]
    position: int


class GetProductVariantResponse(BaseModel):
    """Позиция внутри результата get_product с собственным и эффективным контентом."""

    id: UUID
    selection: dict[str, str]
    virtual: bool
    downloadable: bool
    content: dict[str, str] | None
    locales: tuple[str, ...]
    effective_title: str | None
    title_source: str | None


class GetProductAttributeValueResponse(BaseModel):
    """Общее enum-значение в HTTP-контракте get_product."""

    attribute_id: UUID
    option_id: UUID
    visible: bool
    position: int


class GetProductResponse(BaseModel):
    """Карточка Product с полной типизированной структурой чтения."""

    id: UUID
    kind: str
    product_type_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    title: str | None
    axes: tuple[GetProductAxisResponse, ...]
    default_selection: dict[str, str] | None
    variants: tuple[GetProductVariantResponse, ...]

    attribute_values: tuple[GetProductAttributeValueResponse, ...]
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
    tag_ids: tuple[UUID, ...]
