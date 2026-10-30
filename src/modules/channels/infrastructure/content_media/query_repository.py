from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.content_media.contracts import MediaReadRow
from src.modules.channels.infrastructure.content_media.mapper import ContentMediaMapper
from src.modules.channels.infrastructure.persistence.models.content_media import (
    ContentMediaModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel,
)
from src.modules.channels.infrastructure.product_representation.document import (
    decode_overrides,
)


class SqlAlchemyContentMediaQueryRepository:
    """Читает только собственные таблицы Channels; не блокирует владельцев ссылок."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant-сессию."""
        self._session = session

    async def get(self, identifier: UUID) -> MediaReadRow | None:
        """Ограничивает media текущей tenant-схемой."""
        media, connection = ContentMediaModel.__table__, ConnectionModel.__table__
        row = (
            (
                await self._session.execute(
                    select(media, connection.c.channel_id)
                    .join(connection, connection.c.id == media.c.connection_id)
                    .where(media.c.id == identifier)
                )
            )
            .mappings()
            .one_or_none()
        )
        return ContentMediaMapper.to_projection(row) if row else None

    async def groups(self, connection_id: UUID) -> tuple[UUID, ...]:
        """Читает лишь группы с явным разрешением; фактическую галерею проверяет builder."""
        group, rep = (
            CatalogBindingGroupModel.__table__,
            ProductRepresentationModel.__table__,
        )
        return tuple(
            (
                await self._session.scalars(
                    select(group.c.id)
                    .join(rep, rep.c.binding_group_id == group.c.id)
                    .where(
                        group.c.connection_id == connection_id,
                        rep.c.export_enabled.is_(True),
                    )
                    .order_by(group.c.id)
                )
            ).all()
        )

    async def used_images(self, file_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        """Учитывает неактивные локали overrides; кеш ready не удерживает файл навсегда."""
        if not file_ids:
            return ()
        wanted = set(file_ids)
        table = ProductRepresentationModel.__table__
        rows = (
            await self._session.execute(
                select(table.c.overrides_schema, table.c.overrides_data)
            )
        ).mappings()
        used: set[UUID] = set()
        for row in rows:
            value = decode_overrides(
                schema=row["overrides_schema"], document=row["overrides_data"]
            )
            used.update(
                identifier.uuid
                for identifier in value.file_ids()
                if identifier.uuid in wanted
            )
        media = ContentMediaModel.__table__
        used.update(
            (
                await self._session.scalars(
                    select(media.c.file_id).where(
                        media.c.file_id.in_(file_ids),
                        media.c.transfer_status == "in_flight",
                    )
                )
            ).all()
        )
        return tuple(sorted(used))
