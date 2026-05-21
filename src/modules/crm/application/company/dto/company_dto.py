from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CompanyDTO:
    """DTO компании, возвращаемый use case и query-репозиторием."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    legal_name: str
