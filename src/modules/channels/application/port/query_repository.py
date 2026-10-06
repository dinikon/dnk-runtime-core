from typing import Protocol
from uuid import UUID

from src.modules.channels.application.query.get_channel.dto import ChannelDetailsDTO
from src.modules.channels.application.query.list_channels.dto import ChannelListItemDTO


class ChannelQueryRepositoryProtocol(Protocol):
    """Читает безопасные проекции в tenant-контексте внешнего UoW."""

    async def get(self, channel_id: UUID) -> ChannelDetailsDTO | None:
        """Возвращает карточку канала или None без чтения credentials."""
        ...

    async def list_all(self) -> tuple[ChannelListItemDTO, ...]:
        """Возвращает строки списка каналов текущего tenant."""
        ...
