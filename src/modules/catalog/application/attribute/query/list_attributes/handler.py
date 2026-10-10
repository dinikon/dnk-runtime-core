from src.modules.catalog.application.attribute.port.query_repository import (
    AttributeQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.attribute.query.list_attributes.query import (
    ListAttributesQuery,
)
from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    ListAttributesPageDTO,
)


class ListAttributesHandler:
    """Читает проекцию list_attributes без восстановления агрегата."""

    def __init__(
        self,
        repository: AttributeQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порт проекций и согласованного чтения."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: ListAttributesQuery) -> ListAttributesPageDTO:
        """Проверяет параметры и возвращает собственный DTO сценария."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        if query.page < 1 or not 1 <= query.page_size <= 100:
            raise InvalidCatalogValueError("Некорректная пагинация.")
        return await self._repository.list_page(
            query.locale, query.search, query.page, query.page_size
        )
