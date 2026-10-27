from src.modules.channels.application.port.query_repository import (
    ChannelQueryRepository,
)
from src.modules.channels.application.service.read_state import ChannelReadState
from src.modules.channels.application.query.list_channels.query import ListChannelsQuery
from src.modules.channels.application.query.list_channels.dto import ListChannelsDTO


class ListChannelsHandler:
    """Читает публичную проекцию и актуальность проверки."""

    def __init__(
        self, repository: ChannelQueryRepository, state: ChannelReadState
    ) -> None:
        """Принимает порты чтения текущего tenant."""
        self.repository, self.state = repository, state

    async def execute(self, query: ListChannelsQuery) -> ListChannelsDTO:
        """Возвращает конкретный результат запроса."""
        rows, total = await self.repository.list(
            query.search, query.platform_kind, query.status, query.offset, query.limit
        )
        return ListChannelsDTO(
            await self.state.enrich(query.tenant_id, rows),
            total,
            query.offset,
            query.limit,
        )
