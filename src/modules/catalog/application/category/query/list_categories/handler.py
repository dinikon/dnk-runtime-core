from src.modules.catalog.application.category.port.query_repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.category.query.list_categories.query import (
    ListCategoriesQuery,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    ListCategoriesPageDTO,
)


class ListCategoriesHandler:
    """Читает проекцию list_categories без восстановления агрегата."""

    def __init__(
        self,
        repository: CategoryQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порт проекций и согласованного чтения."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: ListCategoriesQuery) -> ListCategoriesPageDTO:
        """Проверяет параметры и возвращает собственный DTO сценария."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        if query.page < 1 or not 1 <= query.page_size <= 100:
            raise InvalidCatalogValueError("Некорректная пагинация.")
        return await self._repository.list_page(
            query.locale,
            query.search,
            query.page,
            query.page_size,
            query.parent_id,
            query.roots_only,
        )
