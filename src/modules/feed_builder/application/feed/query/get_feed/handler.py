from dataclasses import replace
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.feed.query.get_feed.query import GetFeedQuery
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError


class GetFeedHandler:
    """Читает карточку через порт проекций."""

    def __init__(self, repository: FeedQueryRepositoryProtocol) -> None:
        """Принимает репозиторий текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetFeedQuery) -> FeedDetailsDTO:
        """Возвращает карточку или сообщает об отсутствии."""
        result = await self._repository.get_details(query.feed_id)
        if result is None:
            raise FeedNotFoundError("Feed не найден.")
        if "categories" in result.schema:
            return replace(result, schema=schema_document(decode_schema(result.schema)))
        return result
