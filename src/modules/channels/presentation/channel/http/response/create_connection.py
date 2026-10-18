from uuid import UUID
from pydantic import BaseModel


class CreateConnectionResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария create_connection."""

    channel_id: UUID
    connection_id: UUID
    revision: int
    verification_job_id: UUID
