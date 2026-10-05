from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AddTenantLocaleResultDTO:
    """Результат добавления локали."""

    code: str
    created_at: datetime
    created_by: UUID
