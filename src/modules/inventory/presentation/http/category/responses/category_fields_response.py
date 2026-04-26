from uuid import UUID

from pydantic import BaseModel


class CategoryFieldOptionResponseSchema(BaseModel):
    """Pydantic-схема одной опции поля модели категории."""

    value: str
    label: str


class CategoryFieldDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания одного поля модели категории."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    kind: str
    is_nullable: bool
    default_value: str | None
    options: list[CategoryFieldOptionResponseSchema]


class CategoryObjectDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания объекта product_category."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str


class CategoryFieldsResponseSchema(BaseModel):
    """Pydantic-схема ответа с описанием модели категории товаров."""

    object: CategoryObjectDescriptionResponseSchema
    fields: list[CategoryFieldDescriptionResponseSchema]
