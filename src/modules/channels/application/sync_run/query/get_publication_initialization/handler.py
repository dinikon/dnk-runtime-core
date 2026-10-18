from src.modules.channels.application.sync_run.query.get_publication_initialization.query import (
    GetPublicationInitializationQuery,
)
from src.modules.channels.application.sync_run.query.get_publication_initialization.dto import (
    GetPublicationInitializationResultDTO,
)
from src.modules.channels.application.sync_run.port.query_repository import (
    SyncRunQueryRepositoryProtocol,
)


class GetPublicationInitializationHandler:
    """Выполняет чтение get_publication_initialization без write repository и восстановления агрегатов."""

    def __init__(self, repository: SyncRunQueryRepositoryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.repository = repository

    async def execute(
        self, query: GetPublicationInitializationQuery
    ) -> GetPublicationInitializationResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        return await self.repository.get_publication_initialization(query)
