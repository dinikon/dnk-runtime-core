from uuid import UUID
from datetime import datetime
from collections.abc import Mapping
from typing import cast
from sqlalchemy import select, func, or_, any_, bindparam
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PgUUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
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
