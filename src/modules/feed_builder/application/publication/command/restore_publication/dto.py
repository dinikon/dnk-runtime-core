from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RestorePublicationResultDTO:
    """Возвращает подтверждённое состояние участия и его версию."""

    id: UUID
    status: str
    version: int
    updated_at: datetime
