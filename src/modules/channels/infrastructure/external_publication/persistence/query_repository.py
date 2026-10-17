from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.external_publication.query.list_publications.dto import (
    PublicationPageDTO,
)
from src.modules.channels.application.external_publication.query.get_publication.dto import (
    PublicationDetailsDTO,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_mapper import (
    PublicationQueryMapper,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel


class SqlAlchemyPublicationQueryRepository:
    """Читает безопасные проекции публикаций текущего подключения."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию общего UoW."""
        self._session = session

    async def list(
        self, channel_id: UUID, offset: int, limit: int
    ) -> PublicationPageDTO:
        """Пагинирует верхние ресурсы; вариации Woo доступны в деталях родителя."""
        p = ExternalPublicationModel.__table__
        child = p.alias("child")
        scope = (
            p.c.channel_id == channel_id,
            p.c.connection_revision == ChannelModel.connection_revision,
            p.c.resource_type == "product",
        )
        joined = p.join(ChannelModel, ChannelModel.id == p.c.channel_id)
        total = await self._session.scalar(
            select(func.count()).select_from(joined).where(*scope)
        )
        count = (
            select(func.count())
            .where(
                child.c.channel_id == p.c.channel_id,
                child.c.connection_revision == p.c.connection_revision,
                child.c.parent_external_id == p.c.external_id,
                child.c.last_run_id == p.c.last_run_id,
            )
            .correlate(p)
            .scalar_subquery()
        )
        doc = p.c.document
        rows = (
            (
                await self._session.execute(
                    select(
                        p.c.id,
                        p.c.external_id,
                        doc["title"].as_string().label("title"),
                        doc["sku"].as_string().label("sku"),
                        doc["images"][0]["url"].as_string().label("thumbnail_url"),
                        doc["price"].as_string().label("price"),
                        doc["currency"].as_string().label("currency"),
                        doc["availability"].as_string().label("availability"),
                        doc["source_status"].as_string().label("source_status"),
                        count.label("variations_count"),
                        p.c.observed_at,
                    )
                    .select_from(joined)
                    .where(*scope)
                    .order_by(p.c.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .mappings()
            .all()
        )
        return PublicationPageDTO(
            tuple(PublicationQueryMapper.to_list_item(row) for row in rows),
            total or 0,
            offset,
            limit,
        )

    async def get(
        self, channel_id: UUID, publication_id: UUID
    ) -> PublicationDetailsDTO | None:
        """Читает документ и связанные позиции с тем же каналом и ревизией."""
        p = ExternalPublicationModel.__table__
        row = (
            (
                await self._session.execute(
                    select(
                        p.c.id,
                        p.c.channel_id,
                        p.c.external_id,
                        p.c.resource_type,
                        p.c.revision,
                        p.c.observed_at,
                        p.c.connection_revision,
                        p.c.last_run_id,
                        p.c.document,
                    )
                    .join(ChannelModel, ChannelModel.id == p.c.channel_id)
                    .where(
                        p.c.channel_id == channel_id,
                        p.c.id == publication_id,
                        p.c.connection_revision == ChannelModel.connection_revision,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        children = (
            (
                await self._session.execute(
                    select(p.c.id, p.c.external_id, p.c.document)
                    .where(
                        p.c.channel_id == channel_id,
                        p.c.connection_revision == row["connection_revision"],
                        p.c.parent_external_id == row["external_id"],
                        p.c.last_run_id == row["last_run_id"],
                    )
                    .order_by(p.c.external_id)
                )
            )
            .mappings()
            .all()
        )
        return PublicationQueryMapper.to_details(row, children)
