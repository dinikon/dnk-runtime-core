from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)

from src.modules.catalog.domain.product.error import VariantNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product.query.get_variant.query import (
    GetVariantQuery,
)
from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantDetailsDTO,
)


class GetVariantHandler:
    """Координирует get_variant; инварианты и переходы принадлежат Domain."""

    def __init__(
        self, repository: ProductQueryRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetVariantQuery) -> GetVariantDetailsDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_variant(
            query.product_id, query.variant_id, query.locale
        )
        if result is None:
            raise VariantNotFoundError("Позиция отсутствует в Product.")
        return result
