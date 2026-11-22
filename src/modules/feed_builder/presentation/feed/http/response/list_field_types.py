from pydantic import BaseModel


class FieldTypeResponse(BaseModel):
    """Передаёт возможности одного типа."""

    kind: str
    label: str
    supports_locale: bool
    supports_currency: bool
    editable_modes: tuple[str, ...]


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
