from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.product_type.command.delete_product_type.command import (
    DeleteProductTypeCommand,
)


class DeleteProductTypeHandler:
    """Координирует delete_product_type; инварианты и переходы принадлежат Domain."""

    def __init__(
        self, repository: ProductTypeRepositoryProtocol, lock: CatalogMutationLockPort
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, command: DeleteProductTypeCommand) -> None:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.product_type_id)
        entity.ensure_revision(command.expected_revision)
        entity.ensure_deletable(await self._repository.is_used(entity.id))
        await self._repository.delete(entity)
