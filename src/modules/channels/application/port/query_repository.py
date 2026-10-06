from typing import Protocol
from uuid import UUID
from src.modules.channels.application.query.get_channel.dto import ChannelDTO


class ChannelQueryRepositoryProtocol(Protocol):
    async def get(self, channel_id: UUID) -> ChannelDTO | None: ...
    async def list_all(self) -> tuple[ChannelDTO, ...]: ...
