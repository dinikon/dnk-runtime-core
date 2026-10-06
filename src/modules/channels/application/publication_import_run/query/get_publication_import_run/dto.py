from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublicationImportRunDetailsDTO:
    """Передаёт безопасный прогресс импорта без credentials и курсора."""

    id: UUID
    channel_id: UUID
    status: str
    pages: int
    resources: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
