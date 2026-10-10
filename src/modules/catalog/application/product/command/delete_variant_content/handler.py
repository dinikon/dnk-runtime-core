from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope

from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product.command.delete_variant_content.command import (
    DeleteVariantContentCommand,
)


class DeleteVariantContentHandler:
    """Координирует delete_variant_content; инварианты и переходы принадлежат Domain."""

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

    async def execute(self, command: DeleteVariantContentCommand) -> None:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        product.find_variant(command.variant_id)
        product.delete_content(
            LocaleVO(command.locale),
            ContentScope.VARIANT,
            command.actor_id,
            self._clock.now(),
            variant_id=command.variant_id,
        )
        await self._repository.save(product)
