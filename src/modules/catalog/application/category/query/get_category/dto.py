from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCategoryDetailsDTO:
    """Карточка справочника в сценарии get_category, без locale fallback."""

    id: UUID
    label: str | None
    revision: int
    locales: tuple[str, ...]
    parent_id: UUID | None
    child_count: int
