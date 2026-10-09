from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope

from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product.command.delete_product_content.command import (
    DeleteProductContentCommand,
)


class DeleteProductContentHandler:
    """Координирует delete_product_content; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock

    async def execute(self, command: DeleteProductContentCommand) -> None:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        product.delete_content(
            LocaleVO(command.locale),
            ContentScope.PRODUCT,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(product)
