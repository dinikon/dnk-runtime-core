from src.modules.files.application.storage_provider.query.list_providers.query import (
    ListProvidersQuery,
)
from src.modules.files.application.storage_provider.query.list_providers.dto import (
    ProviderListItemDTO,
)
from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)


class ListProvidersHandler:
    """Читает проекции для read-only консоли."""

    def __init__(self, repository: StorageQueryRepositoryProtocol) -> None:
        """Принимает репозиторий проекций текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListProvidersQuery
    ) -> tuple[ProviderListItemDTO, ...]:
        """Возвращает специализированные DTO без восстановления агрегатов."""
        return await self._repository.providers()
