"""HTTP-ответ конкретного сценария Channels."""

from uuid import UUID

from pydantic import BaseModel


class StartSyncRunResponse(BaseModel):
    """Не раскрывает документы хранения и данные доступа."""

    id: UUID
    status: str
