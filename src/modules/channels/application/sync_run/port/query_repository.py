from typing import Protocol
from src.modules.channels.application.sync_run.query.get_publication_initialization.query import (
    GetPublicationInitializationQuery,
)
from src.modules.channels.application.sync_run.query.get_publication_initialization.dto import (
    GetPublicationInitializationResultDTO,
)


class SyncRunQueryRepositoryProtocol(Protocol):
    """Определяет чтение готовых DTO без ORM во внутренних слоях."""

    async def get_publication_initialization(
        self, query: GetPublicationInitializationQuery
    ) -> GetPublicationInitializationResultDTO:
        """Читает проекцию get_publication_initialization в текущей tenant-схеме."""
        ...
