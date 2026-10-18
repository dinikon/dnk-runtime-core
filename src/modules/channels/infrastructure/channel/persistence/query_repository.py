from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.channel.persistence.query_mapper import (
    ChannelQueryMapper,
)
from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.application.channel.query.get_channel.dto import (
    GetChannelResultDTO,
)
from src.modules.channels.application.channel.query.list_channels.query import (
    ListChannelsQuery,
)
from src.modules.channels.application.channel.query.list_channels.dto import (
    ListChannelsResultDTO,
)
from src.modules.channels.application.channel.query.get_connection.query import (
    GetConnectionQuery,
)
from src.modules.channels.application.channel.query.get_connection.dto import (
    GetConnectionResultDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyChannelQueryRepository:
    """Читает явные SQL-проекции без secret fields и write repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего tenant UoW."""
        self.session = session

    async def get_channel(self, query: GetChannelQuery) -> GetChannelResultDTO:
        """Читает корень с optional summary единственного подключения."""
        c, r = (ChannelModel.__table__, ConnectionModel.__table__)
        row = (
            (
                await self.session.execute(
                    select(
                        c.c.id.label("channel_id"),
                        c.c.name,
                        c.c.platform_kind,
                        c.c.is_enabled,
                        c.c.is_archived,
                        c.c.revision,
                        r.c.id.label("connection_id"),
                        r.c.verification_status,
                        r.c.is_paused,
                    )
                    .select_from(c.outerjoin(r, r.c.channel_id == c.c.id))
                    .where(c.c.id == query.channel_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("channel_not_found")
        return ChannelQueryMapper.to_details(row)

    async def list_channels(self, query: ListChannelsQuery) -> ListChannelsResultDTO:
        """Возвращает стабильную страницу каналов и общее количество."""
        c, r = (ChannelModel.__table__, ConnectionModel.__table__)
        total = await self.session.scalar(select(func.count()).select_from(c))
        rows = (
            (
                await self.session.execute(
                    select(
                        c.c.id.label("channel_id"),
                        c.c.name,
                        c.c.platform_kind,
                        c.c.is_enabled,
                        c.c.is_archived,
                        c.c.revision,
                        r.c.id.label("connection_id"),
                        r.c.verification_status,
                        r.c.is_paused,
                    )
                    .select_from(c.outerjoin(r, r.c.channel_id == c.c.id))
                    .order_by(c.c.id)
                    .offset(query.offset)
                    .limit(query.limit)
                )
            )
            .mappings()
            .all()
        )
        return ListChannelsResultDTO(
            tuple((ChannelQueryMapper.to_list_item(row) for row in rows)), total
        )

    async def get_connection(self, query: GetConnectionQuery) -> GetConnectionResultDTO:
        """Возвращает настройки с presence-флагами вместо зашифрованных секретов."""
        c, r = (ChannelModel.__table__, ConnectionModel.__table__)
        row = (
            (
                await self.session.execute(
                    select(
                        c.c.id.label("channel_id"),
                        r.c.id.label("connection_id"),
                        c.c.revision,
                        r.c.endpoint,
                        r.c.locales,
                        r.c.currency,
                        r.c.resource_identity,
                        r.c.verification_status,
                        r.c.verification_job_id,
                        r.c.generation,
                        r.c.is_paused,
                        (r.c.credentials_ciphertext != "").label("credentials_present"),
                        r.c.candidate_ciphertext.is_not(None).label(
                            "candidate_present"
                        ),
                        r.c.reason_code,
                        r.c.scope_limitations,
                    )
                    .select_from(c.join(r, r.c.channel_id == c.c.id))
                    .where(c.c.id == query.channel_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("connection_not_configured")
        return ChannelQueryMapper.to_connection(row)
