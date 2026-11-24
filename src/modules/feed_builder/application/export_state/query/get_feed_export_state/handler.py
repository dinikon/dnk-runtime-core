from src.modules.feed_builder.application.export_state.query.dto import (
    FeedExportStateDTO,
)
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.export_state.query.get_feed_export_state.query import (
    GetFeedExportStateQuery,
)


class GetFeedExportStateHandler:
    """Читает состояние Feed Builder по контракту проекций."""

    def __init__(self, queries: FeedExportQueryRepositoryProtocol) -> None:
        """Получает read-side порт текущего tenant."""
        self._queries = queries

    async def execute(
        self, query: GetFeedExportStateQuery
    ) -> FeedExportStateDTO | None:
        """Возвращает результат запроса."""
        return await self._queries.get(query.feed_id)
