from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product_type.port.query_repository import (
    ProductTypeQueryRepositoryProtocol,
)

from src.modules.catalog.domain.product_type.error import ProductTypeNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product_type.query.get_product_type.query import (
    GetProductTypeQuery,
)
from src.modules.catalog.application.product_type.query.get_product_type.dto import (
    GetProductTypeDetailsDTO,
)


class GetProductTypeHandler:
    """Координирует get_product_type; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductTypeQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetProductTypeQuery) -> GetProductTypeDetailsDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_details(query.product_type_id, query.locale)
        if result is None:
            raise ProductTypeNotFoundError("Объект не найден.")
        return result
