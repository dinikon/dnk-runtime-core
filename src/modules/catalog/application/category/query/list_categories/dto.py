from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CategoryListItemDTO:
    """Строка отдельной проекции list_categories."""

    id: UUID
    label: str | None
    revision: int
    parent_id: UUID | None
    child_count: int


@dataclass(frozen=True, slots=True)
class ListCategoriesPageDTO:
    """Стабильно упорядоченная страница сценария list_categories."""

    items: tuple[CategoryListItemDTO, ...]
    total: int
    page: int
    page_size: int
