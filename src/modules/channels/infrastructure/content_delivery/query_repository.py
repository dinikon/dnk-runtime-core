from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryRow,
)
from src.modules.channels.infrastructure.content_delivery.mapper import (
    ContentDeliveryMapper,
)
from src.modules.channels.infrastructure.persistence.models.content_delivery import (
    ContentDeliveryModel,
)


class SqlAlchemyContentDeliveryQueryRepository:
    """Читает проекции состояния без расшифровки подготовленных запросов."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает ту же tenant-сессию внешней сборки."""
        self._session = session

    async def for_representation(
        self, representation_id: UUID
    ) -> tuple[ContentDeliveryRow, ...]:
        """Возвращает состояния целей в стабильном порядке."""
        table = ContentDeliveryModel.__table__
        rows = (
            await self._session.execute(
                select(table)
                .where(table.c.representation_id == representation_id)
                .order_by(table.c.publication_id)
            )
        ).mappings()
        return tuple(ContentDeliveryMapper.to_projection(row) for row in rows)
