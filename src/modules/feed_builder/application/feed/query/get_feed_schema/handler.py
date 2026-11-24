from dataclasses import replace
from src.modules.feed_builder.application.feed.schema_definition import decode_schema
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.application.feed.query.get_feed_schema.query import (
    GetFeedSchemaQuery,
)
from src.modules.feed_builder.application.feed.query.get_feed_schema.dto import (
    FeedSchemaDetailsDTO,
)
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError


class GetFeedSchemaHandler:
    """Читает проекцию схемы без восстановления Feed и изменения БД."""

    def __init__(self, repository: FeedQueryRepositoryProtocol) -> None:
        """Принимает read-side порт текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetFeedSchemaQuery) -> FeedSchemaDetailsDTO:
        """Возвращает схему, включая архив, или предметную ошибку отсутствия."""
        result = await self._repository.get_schema(query.feed_id)
        if result is None:
            raise FeedNotFoundError("Feed не найден.")
        if "categories" in result.definition:
            return replace(
                result, definition=schema_document(decode_schema(result.definition))
            )
        return result
