from uuid import UUID
from pydantic import BaseModel


class UpdateConnectionSettingsResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария update_connection_settings."""

    channel_id: UUID
    connection_id: UUID
    revision: int
    verification_job_id: UUID | None
