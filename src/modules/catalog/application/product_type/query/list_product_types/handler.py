from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product_type.port.query_repository import (
    ProductTypeQueryRepositoryProtocol,
)

from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product_type.query.list_product_types.query import (
    ListProductTypesQuery,
)
from src.modules.catalog.application.product_type.query.list_product_types.dto import (
    ListProductTypesPageDTO,
)


class ListProductTypesHandler:
    """Координирует list_product_types; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductTypeQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: ListProductTypesQuery) -> ListProductTypesPageDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        if query.page < 1 or not 1 <= query.page_size <= 100:
            raise InvalidCatalogValueError("Некорректная пагинация.")
        return await self._repository.list_page(
            query.locale, query.search, query.page, query.page_size
        )
