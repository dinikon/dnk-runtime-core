from src.modules.shared.domain.value_object.entity_id import EntityIdVO
import hashlib
from sqlalchemy import select, insert, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.channel.persistence.mapper import ChannelMapper


class SqlAlchemyChannelRepository:
    """Хранит один агрегат в channels/channel_connections на внешней сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию с уже выбранной tenant-схемой."""
        self.session = session

    async def get(self, identifier: EntityIdVO, *, for_update: bool = True) -> Channel:
        """Блокирует корень перед изменением и восстанавливает обе строки."""
        table = ChannelModel.__table__
        statement = select(table).where(table.c.id == identifier.uuid)
        if for_update:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).mappings().one_or_none()
        if row is None:
            raise ChannelsNotFoundError("channel_not_found")
        connection = (
            (
                await self.session.execute(
                    select(ConnectionModel.__table__).where(
                        ConnectionModel.channel_id == identifier.uuid
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return ChannelMapper.to_domain(row, connection)

    async def by_connection(self, connection_id: EntityIdVO) -> Channel:
        """Разрешает Connection ID в корень; Entity отдельно не восстанавливает."""
        identifier = await self.session.scalar(
            select(ConnectionModel.channel_id).where(
                ConnectionModel.id == connection_id.uuid
            )
        )
        if identifier is None:
            raise ChannelsNotFoundError("connection_not_found")
        return await self.get(EntityIdVO(identifier))

    async def identity_in_use(
        self, kind: str, identity: str, connection_id: EntityIdVO
    ) -> bool:
        """Сериализует подтверждение identity и проверяет её уникальность."""
        key = hashlib.sha256((kind + ":" + identity).encode()).hexdigest()
        lock = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], signed=True)
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock}
        )
        return (
            await self.session.scalar(
                select(ConnectionModel.id).where(
                    ConnectionModel.resource_key == key,
                    ConnectionModel.id != connection_id.uuid,
                )
            )
            is not None
        )

    async def add(self, channel: Channel) -> None:
        """Вставляет новый корень без commit."""
        await self.session.execute(
            insert(ChannelModel).values(**ChannelMapper.to_values(channel))
        )

    async def save(self, channel: Channel) -> None:
        """Сохраняет корень и его единственную Entity в одной транзакции."""
        values = ChannelMapper.to_values(channel)
        await self.session.execute(
            update(ChannelModel)
            .where(ChannelModel.id == channel.id.uuid)
            .values(**values)
        )
        connection = ChannelMapper.connection_values(channel)
        if connection:
            statement = pg_insert(ConnectionModel).values(**connection)
            await self.session.execute(
                statement.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        key: value for key, value in connection.items() if key != "id"
                    },
                )
            )
