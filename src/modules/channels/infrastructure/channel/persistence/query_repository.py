from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.channel.port.registry import ChannelRegistryPort
from src.modules.channels.application.channel.query.get_channel.dto import (
    ChannelDetailsDTO,
)
from src.modules.channels.application.channel.query.list_channels.dto import (
    ChannelListItemDTO,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.channel.persistence.query_mapper import (
    ChannelQueryMapper,
)


class SqlAlchemyChannelQueryRepository:
    """Читает безопасные проекции на tenant-сессии без выбора ciphertext."""

    def __init__(self, session: AsyncSession, registry: ChannelRegistryPort) -> None:
        """Принимает общую сессию внешнего UoW и порт категорий платформ."""
        self._session = session
        self._registry = registry

    def _select(self) -> Select[Any]:
        """Явно выбирает публичные поля, исключая credentials и будущие поля модели."""
        return select(
            ChannelModel.id,
            ChannelModel.name,
            ChannelModel.kind,
            ChannelModel.config_version,
            ChannelModel.connection_settings,
            ChannelModel.configured_secret_fields,
            ChannelModel.is_active,
            ChannelModel.status,
            ChannelModel.created_at,
            ChannelModel.updated_at,
            ChannelModel.created_by,
            ChannelModel.updated_by,
        )

    async def get(self, channel_id: UUID) -> ChannelDetailsDTO | None:
        """Возвращает карточку канала текущего tenant или None."""
        result = await self._session.execute(
            self._select().where(ChannelModel.id == channel_id)
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return ChannelQueryMapper.to_details(row, self._registry.get(row["kind"]).type)

    async def list_all(self) -> tuple[ChannelListItemDTO, ...]:
        """Возвращает каналы текущего tenant от новых к старым."""
        result = await self._session.execute(
            self._select().order_by(ChannelModel.created_at.desc(), ChannelModel.id)
        )
        return tuple(
            ChannelQueryMapper.to_list_item(row, self._registry.get(row["kind"]).type)
            for row in result.mappings()
        )
