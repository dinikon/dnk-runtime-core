from src.modules.channels.application.content_feed.command.enable_content_feed.command import (
    EnableContentFeedCommand,
)
from src.modules.channels.application.content_feed.command.enable_content_feed.dto import (
    EnableContentFeedResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class EnableContentFeedHandler:
    """Координирует отдельный сценарий enable_content_feed."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Получает сервис на портах одного внешнего UoW."""
        self._management = management

    async def execute(
        self, command: EnableContentFeedCommand
    ) -> EnableContentFeedResultDTO:
        """Возвращает явный результат; commit выполняется внешним UoW."""
        return EnableContentFeedResultDTO(
            await self._management.enable(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                expected_revision=command.expected_revision,
                actor_id=command.actor_id,
            )
        )
