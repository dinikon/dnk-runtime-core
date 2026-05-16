from uuid import UUID

from pydantic import BaseModel


class CompanyFieldOptionResponseSchema(BaseModel):
    """Pydantic-схема одной опции поля CRM-модели."""

    value: str
    label: str


class CompanyFieldDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания одного поля CRM-модели."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    kind: str
    is_nullable: bool
    default_value: str | None
    options: list[CompanyFieldOptionResponseSchema]


class CompanyObjectDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания объекта company."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str


class CompanyFieldsResponseSchema(BaseModel):
    """Pydantic-схема ответа с описанием CRM-модели company."""

    object: CompanyObjectDescriptionResponseSchema
    fields: list[CompanyFieldDescriptionResponseSchema]
