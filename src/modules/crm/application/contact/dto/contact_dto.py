from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactDTO:
    id: UUID

    created_at: datetime
    updated_at: datetime

    first_name: str | None
    last_name: str | None
    middle_name: str | None
