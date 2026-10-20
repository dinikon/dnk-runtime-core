from src.modules.channels.application.content_update.port.queries import (
    ContentUpdateQueries,
)
from src.modules.channels.application.content_update.query.list_content_updates.query import (
    ListContentUpdatesQuery,
)
from src.modules.channels.application.content_update.query.list_content_updates.dto import (
    ListContentUpdatesResultDTO,
)


class ListContentUpdatesHandler:
    """Читает ограниченную историю через query repository."""

    def __init__(self, queries: ContentUpdateQueries) -> None:
        """Получает собственный read порт Channels."""
        self.queries = queries

    async def execute(
        self, query: ListContentUpdatesQuery
    ) -> ListContentUpdatesResultDTO:
        """Возвращает только операции текущего автора выбранного канала."""
        return await self.queries.recent(query.channel_id, query.actor_id)
