from src.modules.channels.application.content_feed.command.revoke_feed_access.command import (
    RevokeFeedAccessCommand,
)
from src.modules.channels.application.content_feed.command.revoke_feed_access.dto import (
    RevokeFeedAccessResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class RevokeFeedAccessHandler:
    """Координирует отдельный сценарий revoke_feed_access."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Получает сервис на портах одного внешнего UoW."""
        self._management = management

    async def execute(
        self, command: RevokeFeedAccessCommand
    ) -> RevokeFeedAccessResultDTO:
        """Возвращает явный результат; commit выполняется внешним UoW."""
        return RevokeFeedAccessResultDTO(
            await self._management.revoke_access(
                channel_id=command.channel_id,
                feed_id=command.feed_id,
                expected_revision=command.expected_revision,
                actor_id=command.actor_id,
            )
        )
