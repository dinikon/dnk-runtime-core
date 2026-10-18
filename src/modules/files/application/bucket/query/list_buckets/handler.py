from src.modules.files.application.bucket.query.list_buckets.query import (
    ListBucketsQuery,
)
from src.modules.files.application.bucket.query.list_buckets.dto import (
    BucketListItemDTO,
)
from src.modules.files.application.port.query_repository import (
    StorageQueryRepositoryProtocol,
)


class ListBucketsHandler:
    """Читает проекции для read-only консоли."""

    def __init__(self, repository: StorageQueryRepositoryProtocol) -> None:
        """Принимает репозиторий проекций текущего tenant."""
        self._repository = repository

    async def execute(self, query: ListBucketsQuery) -> tuple[BucketListItemDTO, ...]:
        """Возвращает специализированные DTO без восстановления агрегатов."""
        return await self._repository.buckets(query.provider_id)
