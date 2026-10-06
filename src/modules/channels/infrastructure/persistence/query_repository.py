from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.port.registry import ChannelRegistryPort
from src.modules.channels.application.query.get_channel.dto import ChannelDTO
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel


class SqlAlchemyChannelQueryRepository:
    """Безопасная проекция: encrypted_secrets даже не выбирается из БД."""

    def __init__(self, session: AsyncSession, registry: ChannelRegistryPort):
        self.session, self.registry = session, registry

    def _select(self):
        return select(
            *(c for c in ChannelModel.__table__.c if c.name != "encrypted_secrets")
        )

    def _dto(self, row):
        values = dict(row)
        values["type"] = self.registry.get(values["kind"]).type.value
        values["configured_secret_fields"] = tuple(values["configured_secret_fields"])
        return ChannelDTO(**values)

    async def get(self, channel_id: UUID):
        row = (
            (
                await self.session.execute(
                    self._select().where(ChannelModel.id == channel_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else self._dto(row)

    async def list_all(self):
        rows = (
            (
                await self.session.execute(
                    self._select().order_by(
                        ChannelModel.created_at.desc(), ChannelModel.id
                    )
                )
            )
            .mappings()
            .all()
        )
        return tuple(self._dto(row) for row in rows)
