from uuid import UUID
from pydantic import BaseModel


class UpdateChannelPolicyResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария update_channel_policy."""

    channel_id: UUID
    revision: int
