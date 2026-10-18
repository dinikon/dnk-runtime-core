from src.modules.channels.application.external_publication.query.get_external_publication.query import (
    GetExternalPublicationQuery,
)
from src.modules.channels.application.external_publication.query.get_external_publication.dto import (
    GetExternalPublicationResultDTO,
)
from src.modules.channels.application.external_publication.port.query_repository import (
    ExternalPublicationQueryRepositoryProtocol,
)


class GetExternalPublicationHandler:
    """Выполняет чтение get_external_publication без write repository и восстановления агрегатов."""

    def __init__(self, repository: ExternalPublicationQueryRepositoryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.repository = repository

    async def execute(
        self, query: GetExternalPublicationQuery
    ) -> GetExternalPublicationResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        return await self.repository.get_external_publication(query)
