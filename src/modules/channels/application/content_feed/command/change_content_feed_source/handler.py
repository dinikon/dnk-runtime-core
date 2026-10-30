from src.modules.channels.application.content_feed.command.change_content_feed_source.command import (
    ChangeContentFeedSourceCommand,
)
from src.modules.channels.application.content_feed.command.change_content_feed_source.dto import (
    ChangeContentFeedSourceResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class ChangeContentFeedSourceHandler:
    """Координирует отдельный сценарий change_content_feed_source."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Получает сервис на портах одного внешнего UoW."""
        self._management = management

    async def execute(
        self, command: ChangeContentFeedSourceCommand
    ) -> ChangeContentFeedSourceResultDTO:
        """Возвращает явный результат; commit выполняется внешним UoW."""
        return ChangeContentFeedSourceResultDTO(
            await self._management.change_source(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                expected_revision=command.expected_revision,
                actor_id=command.actor_id,
                source=command.source,
                source_url=command.source_url,
            )
        )
