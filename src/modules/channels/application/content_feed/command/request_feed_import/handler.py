from src.modules.channels.application.content_feed.command.request_feed_import.command import (
    RequestFeedImportCommand,
)
from src.modules.channels.application.content_feed.command.request_feed_import.dto import (
    RequestFeedImportResultDTO,
)
from src.modules.channels.application.content_feed.service.imports import FeedImports


class RequestFeedImportHandler:
    """Выполняет отдельный сценарий request_feed_import."""

    def __init__(self, imports: FeedImports) -> None:
        """Получает порты одного внешнего UoW."""
        self._imports = imports

    async def execute(
        self, command: RequestFeedImportCommand
    ) -> RequestFeedImportResultDTO:
        """Возвращает конкретный результат; commit остаётся во внешней сборке."""
        return RequestFeedImportResultDTO(
            await self._imports.request(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                actor_id=command.actor_id,
                expected_revision=command.expected_revision,
                expected_delivery_revision=command.expected_delivery_revision,
                request_id=command.request_id,
                force_update=command.force_update,
            )
        )
