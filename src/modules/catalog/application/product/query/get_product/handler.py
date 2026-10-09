from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)

from src.modules.catalog.domain.product.error import ProductNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product.query.get_product.query import (
    GetProductQuery,
)
from src.modules.catalog.application.product.query.get_product.dto import (
    GetProductDetailsDTO,
)


class GetProductHandler:
    """Координирует get_product; инварианты и переходы принадлежат Domain."""

    def __init__(
        self, repository: ProductQueryRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetProductQuery) -> GetProductDetailsDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_details(query.product_id, query.locale)
        if result is None:
            raise ProductNotFoundError("Объект не найден.")
        return result
