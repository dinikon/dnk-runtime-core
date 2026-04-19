from uuid import UUID

from pydantic import BaseModel


class ContactFieldOptionResponseSchema(BaseModel):
    """Pydantic-схема одной опции поля CRM-модели."""

    value: str
    label: str


class ContactFieldDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания одного поля CRM-модели."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: list[ContactFieldOptionResponseSchema]


class ContactObjectDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания объекта contact."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str


class ContactFieldsResponseSchema(BaseModel):
    """Pydantic-схема ответа с описанием CRM-модели contact."""

    object: ContactObjectDescriptionResponseSchema
    fields: list[ContactFieldDescriptionResponseSchema]
