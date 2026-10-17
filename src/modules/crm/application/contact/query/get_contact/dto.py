from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactDetailsDTO:
    """Сохранённые данные контакта с учётом nullable SQL-столбца."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
