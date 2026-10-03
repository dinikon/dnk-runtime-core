from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateCompanyResultDTO:
    id: UUID
    legal_name: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
