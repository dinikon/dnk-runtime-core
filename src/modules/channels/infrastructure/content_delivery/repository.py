from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery
from src.modules.channels.domain.content_delivery.error import ContentDeliveryError
from src.modules.channels.infrastructure.content_delivery.mapper import (
    ContentDeliveryMapper,
)
from src.modules.channels.infrastructure.persistence.models.content_delivery import (
    ContentDeliveryModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyContentDeliveryRepository:
    """Хранит самостоятельные агрегаты под блокировкой общего контекста."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant UoW."""
        self._session = session

    async def get(
        self, representation_id: EntityIdVO, publication_id: EntityIdVO
    ) -> ContentDelivery | None:
        """Блокирует конкретную пару перед доменным переходом."""
        table = ContentDeliveryModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table)
                    .where(
                        table.c.representation_id == representation_id.uuid,
                        table.c.publication_id == publication_id.uuid,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return ContentDeliveryMapper.to_domain(row) if row else None

    async def save(self, delivery: ContentDelivery) -> None:
        """Сохраняет несколько переходов одной блокированной строки без commit."""
        table = ContentDeliveryModel.__table__
        condition = (
            table.c.representation_id == delivery.representation_id.uuid,
            table.c.publication_id == delivery.publication_id.uuid,
        )
        revision = await self._session.scalar(
            select(table.c.revision).where(*condition)
        )
        values = ContentDeliveryMapper.to_values(delivery)
        if revision is None:
            await self._session.execute(insert(table).values(**values))
        elif revision != delivery.revision:
            if revision > delivery.revision:
                raise ContentDeliveryError("content_revision_conflict", conflict=True)
            result = await self._session.execute(
                update(table)
                .where(*condition, table.c.revision == revision)
                .values(**values)
            )
            if result.rowcount != 1:
                raise ContentDeliveryError("content_revision_conflict", conflict=True)

    async def for_representation(
        self, representation_id: EntityIdVO
    ) -> tuple[ContentDelivery, ...]:
        """Загружает цели только для доменных переходов, не для экрана Console."""
        table = ContentDeliveryModel.__table__
        rows = (
            await self._session.execute(
                select(table)
                .where(table.c.representation_id == representation_id.uuid)
                .order_by(table.c.publication_id)
                .with_for_update()
            )
        ).mappings()
        return tuple(ContentDeliveryMapper.to_domain(row) for row in rows)
