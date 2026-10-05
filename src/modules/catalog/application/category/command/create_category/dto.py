from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateCategoryResultDTO:
    id: UUID
    parent_id: UUID | None
    locales: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
