from src.modules.channels.application.content_feed.command.create_content_feed.command import (
    CreateContentFeedCommand,
)
from src.modules.channels.application.content_feed.command.create_content_feed.dto import (
    CreateContentFeedResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class CreateContentFeedHandler:
    """Координирует отдельный сценарий create_content_feed."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Получает сервис на портах одного внешнего UoW."""
        self._management = management

    async def execute(
        self, command: CreateContentFeedCommand
    ) -> CreateContentFeedResultDTO:
        """Возвращает явный результат; commit выполняется внешним UoW."""
        return CreateContentFeedResultDTO(
            await self._management.create(
                channel_id=command.channel_id,
                actor_id=command.actor_id,
                source=command.source,
                source_url=command.source_url,
            )
        )
