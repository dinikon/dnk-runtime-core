from uuid import UUID
from pydantic import BaseModel


class ListChannelsItemResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария list_channels."""

    channel_id: UUID
    name: str
    platform_kind: str
    is_enabled: bool
    is_archived: bool
    revision: int
    connection_id: UUID | None
    verification_status: str | None
    is_paused: bool | None


class ListChannelsResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария list_channels."""

    items: tuple[ListChannelsItemResponse, ...]
    total: int
