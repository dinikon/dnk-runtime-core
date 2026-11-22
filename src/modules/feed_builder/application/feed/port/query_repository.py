from typing import Protocol
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.query.get_feed_schema.dto import (
    FeedSchemaDetailsDTO,
)
from src.modules.feed_builder.application.feed.query.list_feeds.dto import (
    ListFeedsResultDTO,
)


class FeedQueryRepositoryProtocol(Protocol):
    """Читает проекции текущего tenant без восстановления корневого агрегата."""

    async def get_details(self, feed_id: FeedIdVO) -> FeedDetailsDTO | None:
        """Возвращает карточку либо None без создания Feed."""
        ...

    async def get_schema(self, feed_id: FeedIdVO) -> FeedSchemaDetailsDTO | None:
        """Читает только рабочую схему и общую версию без восстановления Feed."""
        ...

    async def list(
        self, *, search: str | None, status: str | None, limit: int, offset: int
    ) -> ListFeedsResultDTO:
        """Возвращает стабильную страницу и общее число совпадений."""
        ...
