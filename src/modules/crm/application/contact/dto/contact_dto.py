from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ContactDTO:
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    first_name: str | None
    middle_name: str | None
