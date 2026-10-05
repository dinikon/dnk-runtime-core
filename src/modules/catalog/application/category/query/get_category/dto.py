from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CategoryTranslationDTO:
    locale: str
    name: str


@dataclass(frozen=True)
class CategoryDetailsDTO:
    id: UUID
    parent_id: UUID | None
    requested_locale: str
    name: str | None
    translations: tuple[CategoryTranslationDTO, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
