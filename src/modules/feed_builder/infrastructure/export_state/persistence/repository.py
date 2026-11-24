from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.domain.export_state.aggregate import FeedExportState
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.infrastructure.export_state.persistence.mapper import (
    FeedExportStateMapper,
)
from src.modules.feed_builder.infrastructure.persistence.models.export_state import (
    FeedExportStateModel,
)


class SqlAlchemyFeedExportStateRepository:
    """Сохраняет состояние в общей tenant-транзакции после блокировки Feed."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает доверенную tenant-сессию."""
        self._session = session

    async def get_for_update(self, feed_id: FeedIdVO) -> FeedExportState:
        """Восстанавливает агрегат или его пустое исходное состояние."""
        row = (
            (
                await self._session.execute(
                    select(FeedExportStateModel.__table__)
                    .where(FeedExportStateModel.feed_id == feed_id.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return (
            FeedExportStateMapper.to_domain(row)
            if row is not None
            else FeedExportState.create(feed_id)
        )

    async def save(self, state: FeedExportState) -> None:
        """Записывает полный агрегат по PK текущего Feed."""
        values = FeedExportStateMapper.to_values(state)
        insert_state = insert(FeedExportStateModel).values(values)
        del values["feed_id"]
        await self._session.execute(
            insert_state.on_conflict_do_update(
                index_elements=[FeedExportStateModel.feed_id], set_=values
            )
        )
