from typing import Protocol
from src.modules.channels.application.external_publication.query.list_external_publications.query import (
    ListExternalPublicationsQuery,
)
from src.modules.channels.application.external_publication.query.list_external_publications.dto import (
    ListExternalPublicationsResultDTO,
)
from src.modules.channels.application.external_publication.query.get_external_publication.query import (
    GetExternalPublicationQuery,
)
from src.modules.channels.application.external_publication.query.get_external_publication.dto import (
    GetExternalPublicationResultDTO,
)


class ExternalPublicationQueryRepositoryProtocol(Protocol):
    """Определяет чтение готовых DTO без ORM во внутренних слоях."""

    async def list_external_publications(
        self, query: ListExternalPublicationsQuery
    ) -> ListExternalPublicationsResultDTO:
        """Читает проекцию list_external_publications в текущей tenant-схеме."""
        ...

    async def get_external_publication(
        self, query: GetExternalPublicationQuery
    ) -> GetExternalPublicationResultDTO:
        """Читает проекцию get_external_publication в текущей tenant-схеме."""
        ...
