from uuid import UUID
from pydantic import BaseModel


class CreateChannelResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария create_channel."""

    channel_id: UUID
    revision: int
    is_enabled: bool
