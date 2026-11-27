from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.domain.access_key.aggregate import FeedAccessKey
from src.modules.feed_builder.domain.access_key.error import AccessKeyNotFoundError
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.infrastructure.access_key.persistence.mapper import (
    FeedAccessKeyMapper,
)
from src.modules.feed_builder.infrastructure.persistence.models.access_key import (
    FeedAccessKeyModel,
)


class SqlAlchemyFeedAccessKeyRepository:
    """Пишет ключи в tenant UoW без самостоятельного commit."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает привязанную к tenant сессию."""
        self._session = session

    async def add(self, key: FeedAccessKey) -> None:
        """Добавляет независимый ключ выбранного фида."""
        await self._session.execute(
            insert(FeedAccessKeyModel).values(FeedAccessKeyMapper.to_insert_values(key))
        )

    async def get_for_update(
        self, feed_id: FeedIdVO, key_id: FeedAccessKeyIdVO
    ) -> FeedAccessKey:
        """Загружает ключ по паре идентификаторов с блокировкой."""
        table = FeedAccessKeyModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table)
                    .where(table.c.feed_id == feed_id.uuid, table.c.id == key_id.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise AccessKeyNotFoundError("Токен фида не найден.")
        return FeedAccessKeyMapper.to_domain(row)

    async def save(self, key: FeedAccessKey) -> None:
        """Обновляет дату отзыва ранее заблокированного ключа."""
        await self._session.execute(
            update(FeedAccessKeyModel)
            .where(
                FeedAccessKeyModel.feed_id == key.feed_id.uuid,
                FeedAccessKeyModel.id == key.id.uuid,
            )
            .values(revoked_at=key.revoked_at)
        )
