from typing import Protocol
from uuid import UUID
from src.modules.channels.application.content_feed.contracts import (
    FeedPublicationKey,
    FeedReadRow,
)


class ContentFeedQueryRepositoryProtocol(Protocol):
    """Читает проекции области и открывает согласованный снимок после commit."""

    async def begin_snapshot(self) -> None:
        """Выбирает изоляцию до первого чтения нового этапа."""
        ...

    async def channel_for_feed(self, feed_id: UUID) -> UUID:
        """Разрешает публичный ID только в схеме текущего tenant."""
        ...

    async def connection_id(self, channel_id: UUID) -> UUID:
        """Получает текущее подключение для создания и проверки принадлежности."""
        ...

    async def details(self, *, channel_id: UUID, feed_id: UUID) -> FeedReadRow:
        """Читает публичную карточку без агрегата."""
        ...

    async def list(self, channel_id: UUID) -> tuple[FeedReadRow, ...]:
        """Читает список без восстановления агрегатов."""
        ...

    async def groups(self, connection_id: UUID) -> tuple[UUID, ...]:
        """Возвращает только группы с разрешённым экспортом."""
        ...

    async def publications(self, connection_id: UUID) -> tuple[FeedPublicationKey, ...]:
        """Читает ключи всех публикаций для обнаружения неоднозначности."""
        ...
