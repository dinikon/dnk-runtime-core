from src.modules.channels.application.content_feed.command.delete_content_feed.command import (
    DeleteContentFeedCommand,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class DeleteContentFeedHandler:
    """Удаляет фид без фиктивного результата."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Принимает сервис общего UoW."""
        self._management = management

    async def execute(self, command: DeleteContentFeedCommand) -> None:
        """Передаёт удаление с CAS; commit остаётся на внешней границе."""
        await self._management.delete(
            channel_id=command.channel_id,
            feed_id=command.feed_id,
            expected_revision=command.expected_revision,
        )
