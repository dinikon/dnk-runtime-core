from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateContactResultDTO:
    """Результат создания контакта с нормализованным именем и аудитом."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
