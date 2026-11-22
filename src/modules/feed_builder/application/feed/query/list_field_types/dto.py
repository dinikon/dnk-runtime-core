from dataclasses import dataclass
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocaleDTO,
)


@dataclass(frozen=True, slots=True)
class FieldTypeItemDTO:
    """Описывает возможности одного типа поля без плоских настроек Entity."""

    kind: str
    label: str
    supports_locale: bool
    supports_currency: bool
    editable_modes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ListFieldTypesResultDTO:
    """Передаёт типы, локали и лимиты конструктора рабочей схемы."""

    items: tuple[FieldTypeItemDTO, ...]
    locales: tuple[SchemaLocaleDTO, ...]
    max_fields: int
    max_transforms: int
