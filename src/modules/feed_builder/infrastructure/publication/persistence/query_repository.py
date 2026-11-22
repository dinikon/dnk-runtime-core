from uuid import UUID
from datetime import datetime
from collections.abc import Mapping
from typing import cast
from sqlalchemy import select, func, or_, any_, bindparam, tuple_
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PgUUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)
from src.modules.feed_builder.application.publication.port.export_source import (
    PublicationCursor,
    PublicationEditorSource,
    PublicationExportSource,
)
from src.modules.feed_builder.infrastructure.publication.persistence.mapper import (
    FeedPublicationMapper,
)
from src.modules.feed_builder.application.publication.port.query_repository import (
    PublicationRecord,
    PublicationPage,
)
from src.modules.feed_builder.infrastructure.persistence.models.publication import (
    FeedPublicationModel as Model,
)


class SqlAlchemyPublicationQueryRepository:
    """Читает только страницу собственных таблиц, без JOIN в Catalog."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию."""
        self._session = session

    @staticmethod
    def _record(row: Mapping[str, object]) -> PublicationRecord:
        """Создаёт read-side запись с реальной версией и датами."""
        return PublicationRecord(
            cast(UUID, row["id"]),
            cast(UUID, row["feed_id"]),
            cast(UUID, row["catalog_item_id"]),
            cast(UUID | None, row["catalog_variant_id"]),
            cast(str, row["status"]),
            cast(int, row["row_version"]),
            cast(datetime, row["created_at"]),
            cast(datetime, row["updated_at"]),
            len(cast(dict[str, object], row["overrides"])),
        )

    async def get(self, identifier: UUID) -> PublicationRecord | None:
        """Не восстанавливает Domain для карточки или проверки доступа."""
        row = (
            (
                await self._session.execute(
                    select(Model.__table__).where(Model.id == identifier)
                )
            )
            .mappings()
            .one_or_none()
        )
        return self._record(row) if row is not None else None

    async def list(
        self,
        feed_id: FeedIdVO,
        status: str | None,
        matched_ids: tuple[UUID, ...] | None,
        limit: int,
        offset: int,
    ) -> PublicationPage:
        """Считает совпадения и возвращает стабильную серверную страницу."""
        conditions = [
            Model.feed_id == feed_id.uuid,
            Model.status == status if status else Model.status != "ARCHIVED",
        ]
        if matched_ids is not None:
            ids = bindparam(
                "matched_ids", list(matched_ids), type_=ARRAY(PgUUID(as_uuid=True))
            )
            conditions.append(
                or_(
                    Model.catalog_item_id == any_(ids),
                    Model.catalog_variant_id == any_(ids),
                )
            )
        total = (
            await self._session.scalar(
                select(func.count()).select_from(Model).where(*conditions)
            )
        ) or 0
        counts = tuple(
            (cast(str, r[0]), cast(int, r[1]))
            for r in (
                await self._session.execute(
                    select(Model.status, func.count())
                    .where(Model.feed_id == feed_id.uuid)
                    .group_by(Model.status)
                )
            ).all()
        )
        rows = (
            await self._session.execute(
                select(Model.__table__)
                .where(*conditions)
                .order_by(Model.created_at.desc(), Model.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).mappings()
        return PublicationPage(tuple(self._record(r) for r in rows), total, counts)

    async def count_enabled(self, feed_id: FeedIdVO) -> int:
        """Считает только включённые публикации."""
        return (
            await self._session.scalar(
                select(func.count())
                .select_from(Model)
                .where(
                    Model.feed_id == feed_id.uuid,
                    Model.status == PublicationStatus.ENABLED.value,
                )
            )
        ) or 0

    async def read_enabled(
        self,
        feed_id: FeedIdVO,
        limit: int,
        before: PublicationCursor | None = None,
    ) -> tuple[PublicationExportSource, ...]:
        """Использует курсор, совпадающий с порядком вкладки товаров."""
        query = select(
            Model.id,
            Model.catalog_item_id,
            Model.catalog_variant_id,
            Model.overrides,
            Model.created_at,
        ).where(
            Model.feed_id == feed_id.uuid,
            Model.status == PublicationStatus.ENABLED.value,
        )
        if before is not None:
            query = query.where(tuple_(Model.created_at, Model.id) < tuple_(*before))
        rows = await self._session.execute(
            query.order_by(Model.created_at.desc(), Model.id.desc()).limit(limit)
        )
        return tuple(
            PublicationExportSource(
                identifier,
                (item_id, variant_id),
                FeedPublicationMapper.read_overrides(overrides),
                created_at,
            )
            for identifier, item_id, variant_id, overrides, created_at in rows
        )

    async def read_for_editor(
        self, feed_id: FeedIdVO, publication_id: UUID
    ) -> PublicationEditorSource | None:
        """Читает ровно одну сохранённую публикацию своего фида."""
        row = (
            await self._session.execute(
                select(
                    Model.catalog_item_id,
                    Model.catalog_variant_id,
                    Model.overrides,
                    Model.created_at,
                    Model.row_version,
                    Model.status,
                ).where(Model.feed_id == feed_id.uuid, Model.id == publication_id)
            )
        ).one_or_none()
        if row is None:
            return None
        item_id, variant_id, overrides, created_at, version, status = row
        return PublicationEditorSource(
            PublicationExportSource(
                publication_id,
                (item_id, variant_id),
                FeedPublicationMapper.read_overrides(overrides),
                created_at,
            ),
            version,
            status == PublicationStatus.ARCHIVED.value,
        )
