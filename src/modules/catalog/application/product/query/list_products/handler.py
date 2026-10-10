from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)

from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product.query.list_products.query import (
    ListProductsQuery,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ListProductsPageDTO,
)


class ListProductsHandler:
    """Координирует list_products; инварианты и переходы принадлежат Domain."""

    def __init__(
        self, repository: ProductQueryRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: ListProductsQuery) -> ListProductsPageDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        if query.page < 1 or not 1 <= query.page_size <= 100:
            raise InvalidCatalogValueError("Некорректная пагинация.")
        if query.kind not in {None, "simple", "variable"}:
            raise InvalidCatalogValueError("Неизвестный вид товара.")
        return await self._repository.list_page(
            query.locale,
            query.search,
            query.page,
            query.page_size,
            query.product_type_id,
            query.kind,
        )
