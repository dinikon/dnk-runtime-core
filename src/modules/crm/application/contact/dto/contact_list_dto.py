from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactListDTO:
    items: Sequence[ContactListItemDTO]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ContactListItemDTO:
    id: UUID

    created_at: datetime
    updated_at: datetime

    first_name: str | None
    last_name: str | None
    middle_name: str | None
