from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.value_object.identifier import ChannelIdVO
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.mapper import (
    to_values,
    restore_channel,
)


class SqlAlchemyChannelRepository:
    """Записывает агрегат в tenant-сессию; транзакция принадлежит UoW."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, channel: Channel):
        await self.session.execute(insert(ChannelModel).values(**to_values(channel)))

    async def get_for_update(self, channel_id: ChannelIdVO):
        row = (
            await self.session.execute(
                select(ChannelModel)
                .where(ChannelModel.id == channel_id.uuid)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return None if row is None else restore_channel(row)

    async def save(self, channel: Channel):
        values = to_values(channel)
        for key in ("id", "kind", "created_at", "created_by"):
            values.pop(key)
        await self.session.execute(
            update(ChannelModel)
            .where(ChannelModel.id == channel.id.uuid)
            .values(**values)
        )

    async def delete(self, channel_id: ChannelIdVO) -> bool:
        result = await self.session.execute(
            delete(ChannelModel)
            .where(ChannelModel.id == channel_id.uuid)
            .returning(ChannelModel.id)
        )
        return result.scalar_one_or_none() is not None
