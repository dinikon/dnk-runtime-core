from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.publication_import import (
    PublicationImportModel as M,
)
from src.modules.channels.infrastructure.publication_import.persistence.query_mapper import (
    PublicationImportQueryMapper,
)
from src.modules.channels.application.publication_import.query.get_publication_import.dto import (
    GetPublicationImportResultDTO,
)
from src.modules.channels.domain.error import ChannelsNotFoundError


class SqlAlchemyPublicationImportQueries:
    """Читает данные конкретного предпросмотра без write repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию."""
        self.session = session

    async def get(self, identifier: UUID) -> GetPublicationImportResultDTO:
        """Возвращает проекцию, не раскрывая storage URL или credentials."""
        row = (
            (await self.session.execute(select(M.__table__).where(M.id == identifier)))
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("import_preparation_not_found")
        return PublicationImportQueryMapper.to_details(row)
