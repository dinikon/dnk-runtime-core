from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContentBlockListItemDTO:
    """Строка списка конкретного сценария без доменного поведения."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    value_type: str


@dataclass(frozen=True, slots=True)
class ListContentBlocksPageDTO:
    """Результат конкретного сценария list_content_blocks."""

    items: tuple[ContentBlockListItemDTO, ...]
    total: int
    page: int
    page_size: int
