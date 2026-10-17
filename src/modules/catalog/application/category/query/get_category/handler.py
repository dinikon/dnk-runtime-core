from src.modules.catalog.application.category.port.query_repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.category.error import CategoryNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.category.query.get_category.query import (
    GetCategoryQuery,
)
from src.modules.catalog.application.category.query.get_category.dto import (
    GetCategoryDetailsDTO,
)


class GetCategoryHandler:
    """Читает проекцию get_category без восстановления агрегата."""

    def __init__(
        self,
        repository: CategoryQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порт проекций и согласованного чтения."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetCategoryQuery) -> GetCategoryDetailsDTO:
        """Проверяет параметры и возвращает собственный DTO сценария."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_details(query.category_id, query.locale)
        if result is None:
            raise CategoryNotFoundError("Характеристика отсутствует.")
        return result
