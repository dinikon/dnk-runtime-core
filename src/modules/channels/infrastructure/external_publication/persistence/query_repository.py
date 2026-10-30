"""SQL read-side карточек с пагинацией до загрузки разновидностей."""

from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_item import (
    CatalogBindingItemModel,
)


from uuid import UUID

from sqlalchemy import select, func, or_, Select, exists
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationConnectionReadRow,
    PublicationReadRow,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationData,
    PublicationKind,
)
from src.modules.channels.infrastructure.persistence.models.channel import ChannelModel
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.channel.persistence.settings import (
    platform_settings,
)


class SqlAlchemyPublicationQueryRepository:
    """Не читает ciphertext, raw_data и platform_data для Console."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешней сборки."""
        self.session = session

    async def connection(self, channel_id: UUID) -> PublicationConnectionReadRow | None:
        """Читает минимальный контекст канала."""
        c, channel = ConnectionModel, ChannelModel
        row = (
            await self.session.execute(
                select(
                    c.id,
                    c.config_revision,
                    channel.platform_kind,
                    c.config_version,
                    c.endpoint,
                    c.settings,
                )
                .join(channel, channel.id == c.channel_id)
                .where(channel.id == channel_id)
            )
        ).one_or_none()
        return (
            PublicationConnectionReadRow(
                row.id,
                row.config_revision,
                row.platform_kind,
                ConnectionConfigVO.create(
                    version=row.config_version,
                    endpoint=row.endpoint,
                    settings=platform_settings(row.settings),
                ),
            )
            if row
            else None
        )

    def _statement(self) -> Select:
        """Выбирает только поддержанные поля read-проекции."""
        p = ExternalPublicationModel
        return select(
            p.id,
            p.external_id,
            p.kind,
            p.parent_id,
            p.normalized_data,
            p.revision,
            p.last_seen_at,
            SyncRunModel.config_revision.label("observed_config_revision"),
        ).join(SyncRunModel, SyncRunModel.id == p.last_sync_run_id)

    async def list_roots(
        self,
        connection_id: UUID,
        search: str,
        offset: int,
        limit: int,
        binding: str = "",
    ) -> tuple[tuple[PublicationReadRow, ...], int]:
        """Ищет участников, затем пагинирует их уникальные корни."""
        p = ExternalPublicationModel
        filters = [p.connection_id == connection_id, p.parent_id.is_(None)]
        if binding:
            member = p.__table__.alias("binding_member")
            g, i = CatalogBindingGroupModel, CatalogBindingItemModel
            family = (
                select(member.c.id)
                .where(or_(member.c.id == p.id, member.c.parent_id == p.id))
                .correlate(p)
            )
            linked = exists(
                select(g.id).where(
                    g.connection_id == connection_id,
                    or_(
                        g.publication_root_id.in_(family),
                        g.id.in_(
                            select(i.group_id).where(i.publication_id.in_(family))
                        ),
                    ),
                )
            )
            filters.append(linked if binding == "linked" else ~linked)
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = "%" + escaped + "%"
            matches = select(func.coalesce(p.parent_id, p.id)).where(
                p.connection_id == connection_id,
                or_(
                    p.external_id.ilike(pattern, escape="\\"),
                    p.normalized_data["sku"].as_string().ilike(pattern, escape="\\"),
                    p.normalized_data["titles"]["uk"]
                    .as_string()
                    .ilike(pattern, escape="\\"),
                    p.normalized_data["titles"]["ru"]
                    .as_string()
                    .ilike(pattern, escape="\\"),
                    p.normalized_data["titles"]["en"]
                    .as_string()
                    .ilike(pattern, escape="\\"),
                ),
            )
            filters.append(p.id.in_(matches))
        total = await self.session.scalar(
            select(func.count()).select_from(p).where(*filters)
        )
        rows = (
            await self.session.execute(
                self._statement()
                .where(*filters)
                .order_by(p.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return tuple(to_read_row(row) for row in rows), total or 0

    async def get(
        self, connection_id: UUID, publication_id: UUID
    ) -> PublicationReadRow | None:
        """Не допускает чтения чужого подключения по известному UUID."""
        p = ExternalPublicationModel
        row = (
            await self.session.execute(
                self._statement().where(
                    p.connection_id == connection_id, p.id == publication_id
                )
            )
        ).one_or_none()
        return to_read_row(row) if row else None

    async def children(
        self, connection_id: UUID, root_ids: tuple[UUID, ...]
    ) -> tuple[PublicationReadRow, ...]:
        """Получает детей всей страницы одним запросом."""
        if not root_ids:
            return ()
        p = ExternalPublicationModel
        rows = (
            await self.session.execute(
                self._statement()
                .where(p.connection_id == connection_id, p.parent_id.in_(root_ids))
                .order_by(p.external_id, p.id)
            )
        ).all()
        return tuple(to_read_row(row) for row in rows)


def to_read_row(row: Row) -> PublicationReadRow:
    """Создаёт конкретную read-проекцию без восстановления агрегата."""
    return PublicationReadRow(
        row.id,
        row.external_id,
        PublicationKind(row.kind),
        row.parent_id,
        PublicationData.from_document(row.normalized_data),
        row.revision,
        row.last_seen_at,
        row.observed_config_revision,
    )
