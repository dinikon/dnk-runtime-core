from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CategoryDTO:
    """DTO категории товаров, возвращаемый use case и query-репозиторием."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    parent_category_id: UUID | None
