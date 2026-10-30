from src.modules.channels.application.content_feed.command.resume_feed_import.command import (
    ResumeFeedImportCommand,
)
from src.modules.channels.application.content_feed.command.resume_feed_import.dto import (
    ResumeFeedImportResultDTO,
)
from src.modules.channels.application.content_feed.service.imports import FeedImports


class ResumeFeedImportHandler:
    """Выполняет отдельный сценарий resume_feed_import."""

    def __init__(self, imports: FeedImports) -> None:
        """Получает порты одного внешнего UoW."""
        self._imports = imports

    async def execute(
        self, command: ResumeFeedImportCommand
    ) -> ResumeFeedImportResultDTO:
        """Возвращает конкретный результат; commit остаётся во внешней сборке."""
        return ResumeFeedImportResultDTO(
            await self._imports.resume(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                actor_id=command.actor_id,
                expected_revision=command.expected_revision,
                expected_delivery_revision=command.expected_delivery_revision,
            )
        )
