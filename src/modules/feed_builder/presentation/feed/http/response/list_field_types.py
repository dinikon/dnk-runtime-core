from src.modules.feed_builder.application.feed.types import JsonObject
from pydantic import BaseModel


class FieldTypeResponse(BaseModel):
    """Передаёт возможности одного типа."""

    kind: str
    label: str
    supports_locale: bool
    supports_currency: bool
    editable_modes: tuple[str, ...]
    type_id: str
    type_version: int
    forms: JsonObject


class SchemaLocaleResponse(BaseModel):
    """Передаёт доступную локаль."""

    code: str
    name: str


class ListFieldTypesResponse(BaseModel):
    """Передаёт типы, локали и лимиты конструктора."""

    items: tuple[FieldTypeResponse, ...]
    locales: tuple[SchemaLocaleResponse, ...]
    max_fields: int
    max_transforms: int
