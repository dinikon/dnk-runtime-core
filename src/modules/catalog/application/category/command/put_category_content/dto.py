from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PutCategoryContentResultDTO:
    category_id: UUID
    locale: str
    name: str
    updated_at: datetime
    updated_by: UUID
