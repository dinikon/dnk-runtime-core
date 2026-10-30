from src.modules.channels.application.content_feed.command.resolve_feed_import.command import (
    ResolveFeedImportCommand,
)
from src.modules.channels.application.content_feed.command.resolve_feed_import.dto import (
    ResolveFeedImportResultDTO,
)
from src.modules.channels.application.content_feed.service.imports import FeedImports


class ResolveFeedImportHandler:
    """Выполняет отдельный сценарий resolve_feed_import."""

    def __init__(self, imports: FeedImports) -> None:
        """Получает порты одного внешнего UoW."""
        self._imports = imports

    async def execute(
        self, command: ResolveFeedImportCommand
    ) -> ResolveFeedImportResultDTO:
        """Возвращает конкретный результат; commit остаётся во внешней сборке."""
        return ResolveFeedImportResultDTO(
            await self._imports.resolve(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                actor_id=command.actor_id,
                expected_revision=command.expected_revision,
                expected_delivery_revision=command.expected_delivery_revision,
            )
        )
