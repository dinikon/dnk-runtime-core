from src.modules.catalog.application.tag.port.query_repository import (
    TagQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.tag.query.list_tags.query import (
    ListTagsQuery,
)
from src.modules.catalog.application.tag.query.list_tags.dto import (
    ListTagsPageDTO,
)


class ListTagsHandler:
    """Читает проекцию list_tags без восстановления агрегата."""

    def __init__(
        self,
        repository: TagQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порт проекций и согласованного чтения."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: ListTagsQuery) -> ListTagsPageDTO:
        """Проверяет параметры и возвращает собственный DTO сценария."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        if query.page < 1 or not 1 <= query.page_size <= 100:
            raise InvalidCatalogValueError("Некорректная пагинация.")
        return await self._repository.list_page(
            query.locale, query.search, query.page, query.page_size
        )
