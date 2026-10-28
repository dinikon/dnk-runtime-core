from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
)
from src.modules.channels.application.channel.query.get_channel.dto import GetChannelDTO
from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.application.channel.service.read_state import ChannelReadState
from src.modules.channels.domain.channel.error import ChannelNotFoundError


class GetChannelHandler:
    """Читает публичную проекцию и актуальность проверки."""

    def __init__(
        self, repository: ChannelQueryRepository, state: ChannelReadState
    ) -> None:
        """Принимает порты чтения текущего tenant."""
        self.repository, self.state = repository, state

    async def execute(self, query: GetChannelQuery) -> GetChannelDTO:
        """Возвращает конкретный результат запроса."""
        row = await self.repository.get(query.channel_id)
        if row is None:
            raise ChannelNotFoundError("Канал не найден.")
        return GetChannelDTO((await self.state.enrich(query.tenant_id, (row,)))[0])
