from src.modules.channels.application.query.list_channels.dto import ChannelListItemDTO
from src.modules.channels.application.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.application.query.list_channels.query import ListChannelsQuery


class ListChannelsHandler:
    """Координирует чтение списка каналов без загрузки агрегатов."""

    def __init__(self, repository: ChannelQueryRepositoryProtocol) -> None:
        """Принимает порт сценария из внешней сборки зависимостей."""
        self._repository = repository

    async def execute(self, query: ListChannelsQuery) -> tuple[ChannelListItemDTO, ...]:
        """Читает безопасную проекцию без восстановления агрегата и расшифровки."""
        return await self._repository.list_all()
