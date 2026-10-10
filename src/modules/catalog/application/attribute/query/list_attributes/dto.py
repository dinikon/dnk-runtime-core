from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AttributeListItemDTO:
    """Одна строка конкретного списка определений."""

    id: UUID
    code: str
    label: str | None
    revision: int
    option_count: int


@dataclass(frozen=True, slots=True)
class ListAttributesPageDTO:
    """Страница результата list_attributes."""

    items: tuple[AttributeListItemDTO, ...]
    total: int
    page: int
    page_size: int
