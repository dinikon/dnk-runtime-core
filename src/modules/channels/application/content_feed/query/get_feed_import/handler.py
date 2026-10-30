from src.modules.channels.application.content_feed.query.get_feed_import.query import (
    GetFeedImportQuery,
)
from src.modules.channels.application.content_feed.query.get_feed_import.dto import (
    GetFeedImportResultDTO,
)
from src.modules.channels.application.content_feed.service.imports import FeedImports


class GetFeedImportHandler:
    """Читает бизнес-состояние операции, не обращаясь к API Prom."""

    def __init__(self, imports: FeedImports) -> None:
        """Получает сервис проекции состояния и Shared Jobs."""
        self._imports = imports

    async def execute(self, query: GetFeedImportQuery) -> GetFeedImportResultDTO:
        """Возвращает конкретный DTO последней операции."""
        return GetFeedImportResultDTO(
            await self._imports.details(
                channel_id=query.channel_id, feed_id=query.feed_id
            )
        )
