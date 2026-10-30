from src.modules.channels.application.content_feed.query.get_content_feed.query import (
    GetContentFeedQuery,
)
from src.modules.channels.application.content_feed.query.get_content_feed.dto import (
    GetContentFeedResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class GetContentFeedHandler:
    """Реализует конкретный сценарий чтения get_content_feed."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Принимает готовые порты внешней сборки."""
        self._management = management

    async def execute(self, query: GetContentFeedQuery) -> GetContentFeedResultDTO:
        """Передаёт запрос сервису без инфраструктурных типов."""
        return GetContentFeedResultDTO(
            await self._management.get(
                channel_id=query.channel_id, feed_id=query.feed_id
            )
        )
