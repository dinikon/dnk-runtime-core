from uuid import UUID

from pydantic import BaseModel


class BroadcastFieldOptionResponseSchema(BaseModel):
    """Pydantic-схема одной опции поля broadcast."""

    value: str
    label: str


class BroadcastFieldFilterCapabilityResponseSchema(BaseModel):
    """Pydantic schema frontend filter capability for a broadcast field."""

    enabled: bool
    operators: list[str]
    input: str
    value_type: str
    options: list[BroadcastFieldOptionResponseSchema]


class BroadcastFieldSortCapabilityResponseSchema(BaseModel):
    """Pydantic schema frontend sort capability for a broadcast field."""

    enabled: bool


class BroadcastFieldDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания одного поля broadcast."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    kind: str
    is_nullable: bool
    default_value: str | None
    options: list[BroadcastFieldOptionResponseSchema]
    filter: BroadcastFieldFilterCapabilityResponseSchema
    sort: BroadcastFieldSortCapabilityResponseSchema


class BroadcastObjectDescriptionResponseSchema(BaseModel):
    """Pydantic-схема описания объекта broadcast."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str


class BroadcastFieldsResponseSchema(BaseModel):
    """Pydantic-схема ответа с описанием broadcast-модели."""

    object: BroadcastObjectDescriptionResponseSchema
    fields: list[BroadcastFieldDescriptionResponseSchema]


__all__ = [
    "BroadcastFieldDescriptionResponseSchema",
    "BroadcastFieldFilterCapabilityResponseSchema",
    "BroadcastFieldOptionResponseSchema",
    "BroadcastFieldsResponseSchema",
    "BroadcastFieldSortCapabilityResponseSchema",
    "BroadcastObjectDescriptionResponseSchema",
]
