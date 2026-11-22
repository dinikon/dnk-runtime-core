from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class RestorePublicationResponse(BaseModel):
    """Возвращает актуальное участие и версию после конкретного действия."""

    id: UUID
    status: str
    version: int
    updated_at: datetime
