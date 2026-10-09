from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product.command.delete_product.command import (
    DeleteProductCommand,
)


class DeleteProductHandler:
    """Координирует delete_product; инварианты и переходы принадлежат Domain."""

    def __init__(
        self, repository: ProductRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, command: DeleteProductCommand) -> None:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        await self._repository.delete(product)
