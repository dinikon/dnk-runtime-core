from src.modules.channels.application.content_feed.query.get_content_feed_xml.query import (
    GetContentFeedXmlQuery,
)
from src.modules.channels.application.content_feed.query.get_content_feed_xml.dto import (
    GetContentFeedXmlResultDTO,
)
from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)


class GetContentFeedXmlHandler:
    """Реализует конкретный сценарий чтения get_content_feed_xml."""

    def __init__(self, management: ContentFeedManagement) -> None:
        """Принимает готовые порты внешней сборки."""
        self._management = management

    async def execute(
        self, query: GetContentFeedXmlQuery
    ) -> GetContentFeedXmlResultDTO:
        """Передаёт запрос сервису без инфраструктурных типов."""
        return GetContentFeedXmlResultDTO(
            await self._management.public(feed_id=query.feed_id, token=query.token)
        )
