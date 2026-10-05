from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class MoveCategoryResultDTO:
    id: UUID
    parent_id: UUID | None
    updated_at: datetime
    updated_by: UUID
