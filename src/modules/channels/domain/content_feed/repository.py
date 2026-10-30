from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO

from src.modules.channels.domain.content_feed.aggregate import ContentFeed


class ContentFeedRepositoryProtocol(Protocol):
    """Хранит самостоятельный агрегат без управления транзакцией."""

    async def get(self, *, channel_id: EntityIdVO, feed_id: EntityIdVO) -> ContentFeed:
        """Загружает только фид указанного канала текущего tenant."""
        ...

    async def add(self, feed: ContentFeed) -> None:
        """Добавляет выключенный фид, соблюдая уникальность области."""
        ...

    async def save(self, feed: ContentFeed, *, expected_revision: int) -> None:
        """Сохраняет проверенный агрегат с оптимистической блокировкой."""
        ...

    async def delete(self, feed: ContentFeed, *, expected_revision: int) -> None:
        """Удаляет фид только с ожидаемой ревизией."""
        ...
