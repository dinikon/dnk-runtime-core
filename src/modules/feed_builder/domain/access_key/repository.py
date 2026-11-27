from typing import Protocol

from src.modules.feed_builder.domain.access_key.aggregate import FeedAccessKey
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


class FeedAccessKeyRepositoryProtocol(Protocol):
    """Управляет ключами текущего tenant в транзакции сценария."""

    async def add(self, key: FeedAccessKey) -> None:
        """Сохраняет выпущенный ключ с digest."""
        ...

    async def get_for_update(
        self, feed_id: FeedIdVO, key_id: FeedAccessKeyIdVO
    ) -> FeedAccessKey:
        """Блокирует конкретный ключ указанного фида."""
        ...

    async def save(self, key: FeedAccessKey) -> None:
        """Сохраняет состояние отзыва загруженного ключа."""
        ...
