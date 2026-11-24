from src.modules.feed_builder.application.export_state.query.dto import (
    FeedExportIssuesPageDTO,
)
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.export_state.query.list_latest_feed_export_issues.query import (
    ListLatestFeedExportIssuesQuery,
)


class ListLatestFeedExportIssuesHandler:
    """Читает состояние Feed Builder по контракту проекций."""

    def __init__(self, queries: FeedExportQueryRepositoryProtocol) -> None:
        """Получает read-side порт текущего tenant."""
        self._queries = queries

    async def execute(
        self, query: ListLatestFeedExportIssuesQuery
    ) -> FeedExportIssuesPageDTO | None:
        """Возвращает результат запроса."""
        if await self._queries.get(query.feed_id) is None:
            return None
        return await self._queries.list_issues(
            query.feed_id, query.severity, query.limit, query.offset
        )
