from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_mapper import (
    ExternalPublicationQueryMapper,
)
from src.modules.channels.application.external_publication.query.get_external_publication.query import (
    GetExternalPublicationQuery,
)
from src.modules.channels.application.external_publication.query.get_external_publication.dto import (
    GetExternalPublicationResultDTO,
)
from src.modules.channels.application.external_publication.query.list_external_publications.query import (
    ListExternalPublicationsQuery,
)
from src.modules.channels.application.external_publication.query.list_external_publications.dto import (
    ListExternalPublicationsResultDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyExternalPublicationQueryRepository:
    """Читает только локальные публикации с фильтрами и tenant из внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Не выполняет внешних запросов при открытии списка."""
        self.session = session

    async def get_external_publication(
        self, query: GetExternalPublicationQuery
    ) -> GetExternalPublicationResultDTO:
        """Читает одну detail projection либо возвращает предметный not found."""
        row = (
            (
                await self.session.execute(
                    select(ExternalPublicationModel.__table__).where(
                        ExternalPublicationModel.id == query.publication_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("publication_not_found")
        return ExternalPublicationQueryMapper.to_details(row)

    async def list_external_publications(
        self, query: ListExternalPublicationsQuery
    ) -> ListExternalPublicationsResultDTO:
        """Фильтрует core-колонки, не загружая extensions для строк списка."""
        if (
            await self.session.scalar(
                select(ConnectionModel.id).where(
                    ConnectionModel.id == query.connection_id
                )
            )
            is None
        ):
            raise ChannelsNotFoundError("connection_not_found")
        table = ExternalPublicationModel.__table__
        conditions = [table.c.connection_id == query.connection_id]
        if query.search:
            escaped = (
                query.search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            conditions.append(
                or_(
                    table.c.title.ilike("%" + escaped + "%", escape="\\"),
                    table.c.external_sku.ilike("%" + escaped + "%", escape="\\"),
                    table.c.external_id == query.search,
                )
            )
        if query.stock_status:
            conditions.append(table.c.stock_status == query.stock_status)
        total = await self.session.scalar(
            select(func.count()).select_from(table).where(*conditions)
        )
        columns = [
            column
            for column in table.c
            if column.name not in ("extensions", "extension_version", "fingerprint")
        ]
        rows = (
            (
                await self.session.execute(
                    select(*columns)
                    .where(*conditions)
                    .order_by(table.c.id)
                    .offset(query.offset)
                    .limit(query.limit)
                )
            )
            .mappings()
            .all()
        )
        return ListExternalPublicationsResultDTO(
            tuple((ExternalPublicationQueryMapper.to_list_item(row) for row in rows)),
            total,
        )
