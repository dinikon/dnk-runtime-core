from src.modules.channels.application.channel.query.get_connection.query import (
    GetConnectionQuery,
)
from src.modules.channels.application.channel.query.get_connection.dto import (
    GetConnectionResultDTO,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)


class GetConnectionHandler:
    """Выполняет чтение get_connection без write repository и восстановления агрегатов."""

    def __init__(self, repository: ChannelQueryRepositoryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.repository = repository

    async def execute(self, query: GetConnectionQuery) -> GetConnectionResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        return await self.repository.get_connection(query)
