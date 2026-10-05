from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CategoryListItemDTO:
    id: UUID
    parent_id: UUID | None
    name: str | None
