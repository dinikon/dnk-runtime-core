import hashlib
from uuid import UUID

from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.infrastructure.gate import channel_write_lock_key
from src.modules.channels.domain.aggregate import Channel
from src.modules.channels.domain.value_object.resource_identity import (
    ResourceIdentityVO,
)
from src.modules.channels.infrastructure.persistence.mapper import (
    to_domain,
    write_verification,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyChannelRepository:
    """Хранит агрегат в сессии с уже привязанной tenant-схемой."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        """Принимает общую сессию UoW; tenant ID нужен для advisory key."""
        self.session, self.tenant_id = session, tenant_id

    async def get(
        self, channel_id: EntityIdVO, *, for_update: bool = False
    ) -> Channel | None:
        """Блокирует сначала корень, затем читает принадлежащую ему Entity."""
        if for_update and self.session.get_bind().dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": channel_write_lock_key(self.tenant_id, channel_id.uuid)},
            )
        statement = select(ChannelModel).where(ChannelModel.id == channel_id.uuid)
        if for_update:
            statement = statement.with_for_update()
        row = await self.session.scalar(statement)
        if row is None:
            return None
        c = await self.session.scalar(
            select(ConnectionModel).where(ConnectionModel.channel_id == channel_id.uuid)
        )
        if c is None:
            raise RuntimeError("Stored channel has no connection")
        return to_domain(row, c)

    async def save(self, channel: Channel) -> None:
        """Сохраняет обе части агрегата без самостоятельного commit."""
        row = await self.session.get(ChannelModel, channel.id.uuid)
        if row is None:
            row = ChannelModel(id=channel.id.uuid)
            self.session.add(row)
        row.name, row.platform_kind, row.revision = (
            channel.name.value,
            channel.platform_kind,
            channel.revision,
        )
        row.created_at, row.updated_at = channel.created_at, channel.updated_at
        row.created_by, row.updated_by = (
            channel.created_by.uuid,
            channel.updated_by.uuid,
        )
        await self.session.flush()
        c = channel.connection
        stored = await self.session.get(ConnectionModel, c.id.uuid)
        if stored is None:
            stored = ConnectionModel(id=c.id.uuid, channel_id=channel.id.uuid)
            self.session.add(stored)
        stored.config_version, stored.endpoint, stored.settings = (
            c.config.version,
            c.config.endpoint,
            c.config.settings,
        )
        stored.encrypted_credentials, stored.config_revision = (
            c.encrypted_credentials,
            c.config_revision,
        )
        stored.identity_namespace = c.identity.namespace if c.identity else None
        stored.identity_key = c.identity.key if c.identity else None
        stored.verification = write_verification(c.verification)
        await self.session.flush()

    async def delete(self, channel_id: EntityIdVO) -> None:
        """Удаляет подключение и секрет, затем корень агрегата."""
        await self.session.execute(
            delete(ConnectionModel).where(ConnectionModel.channel_id == channel_id.uuid)
        )
        await self.session.execute(
            delete(ChannelModel).where(ChannelModel.id == channel_id.uuid)
        )

    async def identity_available(
        self, channel_id: EntityIdVO, identity: ResourceIdentityVO
    ) -> bool:
        """Сериализует конкурирующие claims; unique constraint остаётся защитой SQL."""
        if self.session.get_bind().dialect.name == "postgresql":
            material = f"channels:identity:{self.tenant_id}:{identity.namespace}:{identity.key}"
            key = int.from_bytes(
                hashlib.sha256(material.encode()).digest()[:8], signed=True
            )
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
            )
        owner = await self.session.scalar(
            select(ConnectionModel.channel_id).where(
                ConnectionModel.identity_namespace == identity.namespace,
                ConnectionModel.identity_key == identity.key,
                ConnectionModel.channel_id != channel_id.uuid,
            )
        )
        return owner is None
