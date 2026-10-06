from src.modules.channels.application.channel.query.get_channel.dto import (
    ChannelDetailsDTO,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)


class GetChannelHandler:
    """Координирует получение безопасной карточки через порт проекций."""

    def __init__(self, repository: ChannelQueryRepositoryProtocol) -> None:
        """Принимает порт сценария из внешней сборки зависимостей."""
        self._repository = repository

    async def execute(self, query: GetChannelQuery) -> ChannelDetailsDTO:
        """Читает безопасную проекцию без восстановления агрегата и расшифровки."""
        result = await self._repository.get(query.channel_id)
        if result is None:
            raise ChannelNotFoundError("Channel not found.")
        return result
