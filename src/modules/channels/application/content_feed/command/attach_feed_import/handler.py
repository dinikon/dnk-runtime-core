from src.modules.channels.application.content_feed.command.attach_feed_import.command import (
    AttachFeedImportCommand,
)
from src.modules.channels.application.content_feed.command.attach_feed_import.dto import (
    AttachFeedImportResultDTO,
)
from src.modules.channels.application.content_feed.service.imports import FeedImports


class AttachFeedImportHandler:
    """Выполняет отдельный сценарий attach_feed_import."""

    def __init__(self, imports: FeedImports) -> None:
        """Получает порты одного внешнего UoW."""
        self._imports = imports

    async def execute(
        self, command: AttachFeedImportCommand
    ) -> AttachFeedImportResultDTO:
        """Возвращает конкретный результат; commit остаётся во внешней сборке."""
        return AttachFeedImportResultDTO(
            await self._imports.attach(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                actor_id=command.actor_id,
                expected_revision=command.expected_revision,
                expected_delivery_revision=command.expected_delivery_revision,
                external_id=command.external_id,
            )
        )
