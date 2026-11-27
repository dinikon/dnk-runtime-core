from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.dto import (
    ListFeedAccessKeysDTO,
)
from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.query import (
    ListFeedAccessKeysQuery,
)
from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.repository import (
    FeedAccessKeyListRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError
from src.modules.shared.domain.time.clock_port import ClockPort


class ListFeedAccessKeysHandler:
    """Возвращает список токенов в текущем tenant."""

    def __init__(
        self, keys: FeedAccessKeyListRepositoryProtocol, clock: ClockPort
    ) -> None:
        """Получает порт проекции и часы для определения срока действия."""
        self._keys, self._clock = keys, clock

    async def execute(self, query: ListFeedAccessKeysQuery) -> ListFeedAccessKeysDTO:
        """Отдаёт метаданные, проверив наличие фида."""
        result = await self._keys.list(query.feed_id, now=self._clock.now())
        if result is None:
            raise FeedNotFoundError("Feed не найден.")
        return result
