from pydantic import BaseModel
from src.modules.channels.presentation.http.response.channel_fields import (
    ChannelResponseFields,
)


class ListChannelItemResponse(ChannelResponseFields):
    """Строка списка каналов."""


class ListChannelsResponse(BaseModel):
    """Страница каналов с независимым HTTP-контрактом."""

    items: tuple[ListChannelItemResponse, ...]
    total: int
    offset: int
    limit: int
