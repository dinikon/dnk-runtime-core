from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer
from src.modules.channels.application.port.query_repository import ChannelReadRow
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.mapper import to_read_row


class SqlAlchemyChannelQueryRepository:
    """Читает SQL-проекции карточек без восстановления доменного агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию внешнего UoW."""
        self.session = session

    async def get(self, channel_id: UUID) -> ChannelReadRow | None:
        """Возвращает безопасную карточку либо None."""
        row = (
            await self.session.execute(
                select(ChannelModel, ConnectionModel)
                .options(defer(ConnectionModel.encrypted_credentials, raiseload=True))
                .join(ConnectionModel, ConnectionModel.channel_id == ChannelModel.id)
                .where(ChannelModel.id == channel_id)
            )
        ).one_or_none()
        return to_read_row(*row) if row is not None else None

    async def list(
        self,
        search: str,
        platform_kind: str | None,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[ChannelReadRow, ...], int]:
        """Применяет фильтры, стабильную сортировку и ограниченную пагинацию."""
        filters = []
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            filters.append(ChannelModel.name.ilike("%" + escaped + "%", escape="\\"))
        if platform_kind:
            filters.append(ChannelModel.platform_kind == platform_kind)
        if status:
            filters.append(ConnectionModel.verification["status"].as_string() == status)
        base = (
            select(ChannelModel, ConnectionModel)
            .options(defer(ConnectionModel.encrypted_credentials, raiseload=True))
            .join(ConnectionModel, ConnectionModel.channel_id == ChannelModel.id)
            .where(*filters)
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = (
            await self.session.execute(
                base.order_by(ChannelModel.updated_at.desc(), ChannelModel.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return tuple(to_read_row(*row) for row in rows), total or 0
