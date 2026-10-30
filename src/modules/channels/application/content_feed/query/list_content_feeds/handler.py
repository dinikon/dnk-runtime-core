from src.modules.channels.application.content_feed.query.list_content_feeds.query import (
    ListContentFeedsQuery,
)
from src.modules.channels.application.content_feed.query.list_content_feeds.dto import (
    ListContentFeedsResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class ListContentFeedsHandler:
    """Реализует конкретный сценарий чтения list_content_feeds."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Принимает готовые порты внешней сборки."""
        self._management = management

    async def execute(self, query: ListContentFeedsQuery) -> ListContentFeedsResultDTO:
        """Передаёт запрос сервису без инфраструктурных типов."""
        return ListContentFeedsResultDTO(await self._management.list(query.channel_id))
