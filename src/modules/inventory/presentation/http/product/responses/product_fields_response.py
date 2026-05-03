from uuid import UUID

from pydantic import BaseModel


class ProductFieldOptionResponseSchema(BaseModel):
    """Pydantic-схема одной опции поля модели товара."""

    value: str
    label: str


class ProductFieldDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания одного поля модели товара."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    kind: str
    is_nullable: bool
    default_value: str | None
    options: list[ProductFieldOptionResponseSchema]


class ProductObjectDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания объекта product."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str


class ProductFieldsResponseSchema(BaseModel):
    """Pydantic-схема ответа с описанием модели товара."""

    object: ProductObjectDescriptionResponseSchema
    fields: list[ProductFieldDescriptionResponseSchema]
