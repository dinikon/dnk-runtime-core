from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.content_update import (
    ContentUpdateRunModel as R,
)
from src.modules.channels.infrastructure.persistence.models.content_update_item import (
    ContentUpdateItemModel as I,
)
from src.modules.channels.infrastructure.persistence.models.channel import (
    ChannelModel as H,
)
from src.modules.channels.infrastructure.content_update.persistence.query_mapper import (
    ContentUpdateQueryMapper,
)
from src.modules.channels.application.content_update.query.get_content_update.dto import (
    GetContentUpdateResultDTO,
)
from src.modules.channels.application.content_update.query.list_content_updates.dto import (
    ListContentUpdatesResultDTO,
    ContentUpdateSummaryDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyContentUpdateQueries:
    """Читает операции в текущей tenant-схеме без write repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self.session = session

    async def scope(self, identifier: UUID) -> tuple[UUID, UUID]:
        """Разрешает ID в канал и автора без тяжёлых снимков."""
        row = (
            await self.session.execute(
                select(R.channel_id, R.actor_id).where(R.id == identifier)
            )
        ).one_or_none()
        if row is None:
            raise ChannelsNotFoundError("content_update_not_found")
        return row[0], row[1]

    async def get(self, identifier: UUID, actor_id: UUID) -> GetContentUpdateResultDTO:
        """Фильтрует автора до чтения текстов чужой операции."""
        row = (
            (
                await self.session.execute(
                    select(R.__table__).where(
                        R.id == identifier, R.actor_id == actor_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("content_update_not_found")
        items = (
            (
                await self.session.execute(
                    select(I.__table__)
                    .where(I.run_id == identifier)
                    .order_by(I.publication_id)
                )
            )
            .mappings()
            .all()
        )
        enabled = bool(
            await self.session.scalar(
                select(H.is_enabled).where(H.id == row["channel_id"])
            )
        )
        return ContentUpdateQueryMapper.to_details(row, items, enabled)

    async def recent(
        self, channel_id: UUID, actor_id: UUID
    ) -> ListContentUpdatesResultDTO:
        """Возвращает последние двадцать операций без описаний и внешней сети."""
        rows = (
            await self.session.execute(
                select(R.id, R.status, R.created_at, func.count(I.publication_id))
                .join(I, I.run_id == R.id)
                .where(R.channel_id == channel_id, R.actor_id == actor_id)
                .group_by(R.id)
                .order_by(R.created_at.desc(), R.id.desc())
                .limit(20)
            )
        ).all()
        return ListContentUpdatesResultDTO(
            tuple(ContentUpdateSummaryDTO(*row) for row in rows)
        )
