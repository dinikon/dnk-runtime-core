from uuid import UUID
from pydantic import BaseModel


class VerifyConnectionResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария verify_connection."""

    channel_id: UUID
    revision: int
    job_id: UUID
