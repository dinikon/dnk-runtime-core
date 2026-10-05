from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PutProductCategoriesResultDTO:
    product_id: UUID
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
    updated_at: datetime
    updated_by: UUID
