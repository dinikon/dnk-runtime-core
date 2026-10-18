from src.modules.channels.application.external_publication.query.list_external_publications.query import (
    ListExternalPublicationsQuery,
)
from src.modules.channels.application.external_publication.query.list_external_publications.dto import (
    ListExternalPublicationsResultDTO,
)
from src.modules.channels.domain.error import ChannelsValidationError
from src.modules.channels.application.external_publication.port.query_repository import (
    ExternalPublicationQueryRepositoryProtocol,
)


class ListExternalPublicationsHandler:
    """Выполняет чтение list_external_publications без write repository и восстановления агрегатов."""

    def __init__(self, repository: ExternalPublicationQueryRepositoryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.repository = repository

    async def execute(
        self, query: ListExternalPublicationsQuery
    ) -> ListExternalPublicationsResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        if query.offset < 0 or not 1 <= query.limit <= 100:
            raise ChannelsValidationError("invalid_pagination")
        if query.stock_status is not None and query.stock_status not in (
            "in_stock",
            "out_of_stock",
            "on_backorder",
            "unknown",
        ):
            raise ChannelsValidationError("invalid_stock_filter")
        return await self.repository.list_external_publications(query)
