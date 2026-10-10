from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TagListItemDTO:
    """Строка отдельной проекции list_tags."""

    id: UUID
    label: str | None
    revision: int


@dataclass(frozen=True, slots=True)
class ListTagsPageDTO:
    """Стабильно упорядоченная страница сценария list_tags."""

    items: tuple[TagListItemDTO, ...]
    total: int
    page: int
    page_size: int
