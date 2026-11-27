from sqlalchemy import Integer, String, select, func, or_, type_coerce
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
from src.modules.feed_builder.infrastructure.feed.persistence.mapper import FeedMapper
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
            await self._session.execute(
                select(FeedModel)
                .where(FeedModel.id == feed_id.uuid)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return (
            None
            if row is None
            else FeedQueryMapper.to_details(FeedMapper.row_values(row))
        )

    async def get_schema(self, feed_id: FeedIdVO) -> FeedSchemaDetailsDTO | None:
        """Читает компактную проекцию рабочей схемы, включая архив."""
        row = (
            await self._session.execute(
                select(
                    FeedModel.id,
                    FeedModel.status,
                    FeedModel.row_version,
                    FeedModel.schema_definition,
                ).where(FeedModel.id == feed_id.uuid)
            )
        ).one_or_none()
        return None if row is None else FeedQueryMapper.to_schema(*row._tuple())

    async def list(
        self, *, search: str | None, status: str | None, limit: int, offset: int
    ) -> ListFeedsResultDTO:
        """Фильтрует, считает и читает стабильную страницу без полного определения."""
        table = FeedModel.__table__
        conditions = [
            (
                FeedModel.status != "ARCHIVED"
                if status is None
                else FeedModel.status == status
            )
        ]
        if search:
            conditions.append(
                or_(
                    FeedModel.name.icontains(search, autoescape=True),
                    FeedModel.code.icontains(search, autoescape=True),
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
                    FeedModel.id,
                    FeedModel.name,
                    FeedModel.code,
                    FeedModel.status,
                    FeedModel.row_version,
                    FeedModel.created_at,
                    FeedModel.updated_at,
                    type_coerce(
                        table.c.export_settings["format_settings"]["format"].astext,
                        String,
                    ).label("format"),
                    type_coerce(
                        func.jsonb_array_length(table.c.schema_definition["fields"]),
                        Integer,
                    ).label("fields_count"),
                )
                .where(*conditions)
                .order_by(FeedModel.updated_at.desc(), FeedModel.id.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return ListFeedsResultDTO(
            items=tuple(FeedQueryMapper.to_list_item(*row._tuple()) for row in rows),
            total=total,
            limit=limit,
            offset=offset,
        )
