from src.modules.channels.application.content_feed.command.rotate_feed_access.command import (
    RotateFeedAccessCommand,
)
from src.modules.channels.application.content_feed.command.rotate_feed_access.dto import (
    RotateFeedAccessResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class RotateFeedAccessHandler:
    """Координирует отдельный сценарий rotate_feed_access."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Получает сервис на портах одного внешнего UoW."""
        self._management = management

    async def execute(
        self, command: RotateFeedAccessCommand
    ) -> RotateFeedAccessResultDTO:
        """Возвращает явный результат; commit выполняется внешним UoW."""
        return RotateFeedAccessResultDTO(
            await self._management.rotate_access(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                expected_revision=command.expected_revision,
                actor_id=command.actor_id,
            )
        )
