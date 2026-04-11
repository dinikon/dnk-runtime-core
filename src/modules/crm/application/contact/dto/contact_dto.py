from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ContactDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str | None
    first_name: str
    middle_name: str | None
    status: str | None
    tags: list[str]
