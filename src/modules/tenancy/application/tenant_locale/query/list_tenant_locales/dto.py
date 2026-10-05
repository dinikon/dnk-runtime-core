from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantLocaleDTO:
    """Публичное представление выбранной локали."""

    code: str
    created_at: datetime
    created_by: UUID
