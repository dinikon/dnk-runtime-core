from src.modules.channels.application.content_feed.command.disable_content_feed.command import (
    DisableContentFeedCommand,
)
from src.modules.channels.application.content_feed.command.disable_content_feed.dto import (
    DisableContentFeedResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class DisableContentFeedHandler:
    """Координирует отдельный сценарий disable_content_feed."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Получает сервис на портах одного внешнего UoW."""
        self._management = management

    async def execute(
        self, command: DisableContentFeedCommand
    ) -> DisableContentFeedResultDTO:
        """Возвращает явный результат; commit выполняется внешним UoW."""
        return DisableContentFeedResultDTO(
            await self._management.disable(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                expected_revision=command.expected_revision,
                actor_id=command.actor_id,
            )
        )
