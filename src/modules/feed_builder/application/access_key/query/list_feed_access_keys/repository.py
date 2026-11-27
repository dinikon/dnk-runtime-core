from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.dto import (
    ListFeedAccessKeysDTO,
)


class FeedAccessKeyListRepositoryProtocol(Protocol):
    """Читает метаданные ключей без восстановления агрегатов."""

    async def list(
        self, feed_id: UUID, *, now: datetime
    ) -> ListFeedAccessKeysDTO | None:
        """Возвращает данные списка или отсутствие самого фида."""
        ...
