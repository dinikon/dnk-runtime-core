from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.mapper import (
    ChannelMapper,
)


class SqlAlchemyChannelRepository:
    """Записывает агрегат в tenant-сессию; транзакция принадлежит UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию общей транзакции внешнего UoW."""
        self._session = session

    async def add(self, channel: Channel) -> None:
        """Добавляет новый агрегат без самостоятельного commit."""
        await self._session.execute(
            insert(ChannelModel).values(**ChannelMapper.to_insert_values(channel))
        )

    async def get_for_update(self, channel_id: ChannelIdVO) -> Channel | None:
        """Блокирует строку и восстанавливает актуальное состояние для PATCH."""
        row = (
            await self._session.execute(
                select(ChannelModel)
                .where(ChannelModel.id == channel_id.uuid)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return None if row is None else ChannelMapper.to_domain(row)

    async def save(self, channel: Channel) -> None:
        """Записывает изменяемые поля агрегата в текущую транзакцию."""
        values = ChannelMapper.to_update_values(channel)
        await self._session.execute(
            update(ChannelModel)
            .where(ChannelModel.id == channel.id.uuid)
            .values(**values)
        )

    async def delete(self, channel_id: ChannelIdVO) -> bool:
        """Удаляет строку вместе с credentials и сообщает о её наличии."""
        result = await self._session.execute(
            delete(ChannelModel)
            .where(ChannelModel.id == channel_id.uuid)
            .returning(ChannelModel.id)
        )
        return result.scalar_one_or_none() is not None
