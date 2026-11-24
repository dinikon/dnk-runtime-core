from uuid import UUID
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.export_state.query.find_used_feed_export_files.query import (
    FindUsedFeedExportFilesQuery,
)


class FindUsedFeedExportFilesHandler:
    """Читает состояние Feed Builder по контракту проекций."""

    def __init__(self, queries: FeedExportQueryRepositoryProtocol) -> None:
        """Получает read-side порт текущего tenant."""
        self._queries = queries

    async def execute(self, query: FindUsedFeedExportFilesQuery) -> tuple[UUID, ...]:
        """Возвращает результат запроса."""
        return await self._queries.used_file_ids(query.file_ids)
