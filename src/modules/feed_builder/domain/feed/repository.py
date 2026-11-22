from typing import Protocol

from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO


class FeedRepositoryProtocol(Protocol):
    """Хранит агрегаты в tenant-сессии внешнего UoW без управления транзакцией."""

    async def add(self, feed: Feed) -> None:
        """Добавляет новый Feed либо сообщает о конфликте кода."""
        ...

    async def get_for_update(self, feed_id: FeedIdVO) -> Feed:
        """Загружает заблокированный Feed либо сообщает об отсутствии."""
        ...

    async def save(self, feed: Feed, *, expected_version: FeedVersionVO) -> None:
        """Сохраняет новое состояние только поверх ожидаемой версии."""
        ...
