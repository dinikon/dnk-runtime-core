from src.modules.shared.domain.value_object.entity_id import EntityIdVO

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.domain.content_feed.aggregate import ContentFeed
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.infrastructure.content_feed.persistence.mapper import (
    ContentFeedMapper,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.content_feed import (
    ContentFeedModel,
)
from sqlalchemy import func
from src.modules.channels.infrastructure.content_feed.delivery_document import (
    DELIVERY_SCHEMA,
    encode_delivery,
)


class SqlAlchemyContentFeedRepository:
    """Применяет CAS к ревизии; не держит row lock во время внешнего HTTP."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую сессию с уже выбранной tenant-схемой."""
        self._session = session

    async def get(self, *, channel_id: EntityIdVO, feed_id: EntityIdVO) -> ContentFeed:
        """Проверяет принадлежность каналу самим SQL-запросом."""
        table, connection = ContentFeedModel.__table__, ConnectionModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table)
                    .join(connection, connection.c.id == table.c.connection_id)
                    .where(
                        table.c.id == feed_id.uuid,
                        connection.c.channel_id == channel_id.uuid,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ContentFeedError("feed_not_found")
        return ContentFeedMapper.to_domain(row)

    async def add(self, feed: ContentFeed) -> None:
        """Переводит конфликт области в безопасную доменную ошибку."""
        try:
            await self._session.execute(
                insert(ContentFeedModel).values(**ContentFeedMapper.to_values(feed))
            )
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) != "23505":
                raise
            raise ContentFeedError("feed_scope_exists", conflict=True) from None

    async def save(self, feed: ContentFeed, *, expected_revision: int) -> None:
        """Проверяет CAS и для идемпотентной операции без смены ревизии."""
        table = ContentFeedModel.__table__
        result = await self._session.execute(
            update(table)
            .where(
                table.c.id == feed.id.uuid,
                table.c.revision == expected_revision,
                func.coalesce(table.c.delivery_state["revision"].as_integer(), 0)
                == feed.delivery.revision,
            )
            .values(**ContentFeedMapper.to_values(feed))
        )
        if result.rowcount != 1:
            raise ContentFeedError("feed_revision_conflict", conflict=True)

    async def delete(self, feed: ContentFeed, *, expected_revision: int) -> None:
        """Удаляет только проверенную версию фида."""
        table = ContentFeedModel.__table__
        result = await self._session.execute(
            delete(table).where(
                table.c.id == feed.id.uuid,
                table.c.revision == expected_revision,
                func.coalesce(table.c.delivery_state["revision"].as_integer(), 0)
                == feed.delivery.revision,
            )
        )
        if result.rowcount != 1:
            raise ContentFeedError("feed_revision_conflict", conflict=True)

    async def save_delivery(
        self,
        feed: ContentFeed,
        *,
        expected_revision: int,
        expected_delivery_revision: int,
    ) -> None:
        """Прогресс не меняет revision/updated_by настроек, используемые XML endpoint."""
        table = ContentFeedModel.__table__
        result = await self._session.execute(
            update(table)
            .where(
                table.c.id == feed.id.uuid,
                table.c.revision == expected_revision,
                func.coalesce(table.c.delivery_state["revision"].as_integer(), 0)
                == expected_delivery_revision,
            )
            .values(
                delivery_schema=DELIVERY_SCHEMA,
                delivery_state=encode_delivery(feed.delivery),
                delivery_request_encrypted=feed.delivery_request_encrypted,
            )
        )
        if result.rowcount != 1:
            raise ContentFeedError("feed_delivery_revision_conflict", conflict=True)
