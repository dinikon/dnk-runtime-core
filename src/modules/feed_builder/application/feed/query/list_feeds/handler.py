from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.feed.query.list_feeds.query import (
    ListFeedsQuery,
)
from src.modules.feed_builder.application.feed.query.list_feeds.dto import (
    ListFeedsResultDTO,
)
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


class ListFeedsHandler:
    """Проверяет параметры страницы и читает готовые проекции."""

    def __init__(self, repository: FeedQueryRepositoryProtocol) -> None:
        """Принимает репозиторий чтения текущего tenant."""
        self._repository = repository

    async def execute(self, query: ListFeedsQuery) -> ListFeedsResultDTO:
        """Возвращает страницу без загрузки агрегатов."""
        if (
            type(query.limit) is not int
            or not 1 <= query.limit <= 100
            or type(query.offset) is not int
            or not 0 <= query.offset <= 9223372036854775807
        ):
            raise InvalidFeedValueError("Недопустимые параметры страницы.")
        if query.status is not None:
            try:
                FeedStatus(query.status)
            except (ValueError, TypeError) as exc:
                raise InvalidFeedValueError("Неизвестный статус Feed.") from exc
        search = query.search
        if search is not None:
            if not isinstance(search, str) or len(search) > 255:
                raise InvalidFeedValueError(
                    "Поиск должен быть строкой до 255 символов."
                )
            search = search.strip() or None
        return await self._repository.list(
            search=search,
            status=query.status,
            limit=query.limit,
            offset=query.offset,
        )
