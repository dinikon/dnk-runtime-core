from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.query.get_feed_schema.dto import (
    FeedSchemaDetailsDTO,
)
from src.modules.feed_builder.application.feed.query.list_feeds.dto import (
    ListFeedsResultDTO,
)
from src.modules.feed_builder.infrastructure.persistence.models.feed import FeedModel
from src.modules.feed_builder.infrastructure.feed.persistence.query_mapper import (
    FeedQueryMapper,
)


class SqlAlchemyFeedQueryRepository:
    """Читает карточки и страницы в tenant-контексте общей сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию, привязанную к tenant до исполнения SQL."""
        self._session = session

    async def get_details(self, feed_id: FeedIdVO) -> FeedDetailsDTO | None:
        """Читает карточку, включая архивную, без Feed.restore."""
        row = (
            (
                await self._session.execute(
                    select(FeedModel.__table__).where(FeedModel.id == feed_id.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else FeedQueryMapper.to_details(row)

    async def get_schema(self, feed_id: FeedIdVO) -> FeedSchemaDetailsDTO | None:
        """Читает компактную проекцию рабочей схемы, включая архив."""
        row = (
            (
                await self._session.execute(
                    select(
                        FeedModel.id,
                        FeedModel.status,
                        FeedModel.row_version,
                        FeedModel.schema_definition,
                    ).where(FeedModel.id == feed_id.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else FeedQueryMapper.to_schema(row)

    async def list(
        self, *, search: str | None, status: str | None, limit: int, offset: int
    ) -> ListFeedsResultDTO:
        """Фильтрует, считает и читает стабильную страницу без полного определения."""
        table = FeedModel.__table__
        conditions = [
            table.c.status != "ARCHIVED" if status is None else table.c.status == status
        ]
        if search:
            conditions.append(
                or_(
                    table.c.name.icontains(search, autoescape=True),
                    table.c.code.icontains(search, autoescape=True),
                )
            )
        total = (
            await self._session.execute(
                select(func.count()).select_from(table).where(*conditions)
            )
        ).scalar_one()
        rows = (
            await self._session.execute(
                select(
                    table.c.id,
                    table.c.name,
                    table.c.code,
                    table.c.status,
                    table.c.row_version,
                    table.c.created_at,
                    table.c.updated_at,
                    table.c.export_settings["format_settings"]["format"].astext.label(
                        "format"
                    ),
                    func.jsonb_array_length(table.c.schema_definition["fields"]).label(
                        "fields_count"
                    ),
                )
                .where(*conditions)
                .order_by(table.c.updated_at.desc(), table.c.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).mappings()
        return ListFeedsResultDTO(
            items=tuple(FeedQueryMapper.to_list_item(row) for row in rows),
            total=total,
            limit=limit,
            offset=offset,
        )
