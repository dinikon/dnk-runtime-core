from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.domain.content_media.aggregate import ContentMedia
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.infrastructure.content_media.mapper import ContentMediaMapper
from src.modules.channels.infrastructure.persistence.models.content_media import (
    ContentMediaModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyContentMediaRepository:
    """Хранит корень на сессии внешнего UoW под общим барьером подключения."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию без управления commit."""
        self._session = session

    async def get(self, identifier: EntityIdVO) -> ContentMedia | None:
        """Блокирует строку перед доменным переходом."""
        table = ContentMediaModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(table.c.id == identifier.uuid).with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return ContentMediaMapper.to_domain(row) if row else None

    async def find(
        self,
        *,
        connection_id: EntityIdVO,
        file_id: EntityIdVO,
        source_fingerprint: str,
        metadata_fingerprint: str,
    ) -> ContentMedia | None:
        """Сериализация отсутствия обеспечивается общей блокировкой Channel."""
        table = ContentMediaModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table)
                    .where(
                        table.c.connection_id == connection_id.uuid,
                        table.c.file_id == file_id.uuid,
                        table.c.source_fingerprint == source_fingerprint,
                        table.c.metadata_fingerprint == metadata_fingerprint,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return ContentMediaMapper.to_domain(row) if row else None

    async def save(self, media: ContentMedia) -> None:
        """Записывает новую ревизию с CAS; равная ревизия не меняет аудит."""
        table = ContentMediaModel.__table__
        revision = await self._session.scalar(
            select(table.c.revision).where(table.c.id == media.id.uuid)
        )
        values = ContentMediaMapper.to_values(media)
        if revision is None:
            await self._session.execute(insert(table).values(**values))
        elif revision != media.revision:
            if revision != media.revision - 1:
                raise ContentMediaError("media_revision_conflict", conflict=True)
            result = await self._session.execute(
                update(table)
                .where(table.c.id == media.id.uuid, table.c.revision == revision)
                .values(**values)
            )
            if result.rowcount != 1:
                raise ContentMediaError("media_revision_conflict", conflict=True)
