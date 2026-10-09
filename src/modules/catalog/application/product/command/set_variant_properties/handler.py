from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.domain.product.error import VariantNotFoundError
from src.modules.catalog.application.product.command.set_variant_properties.command import (
    SetVariantPropertiesCommand,
)
from src.modules.catalog.application.product.command.set_variant_properties.dto import (
    SetVariantPropertiesResultDTO,
)


class SetVariantPropertiesHandler:
    """Координирует set_variant_properties; инварианты и переходы принадлежат Domain."""

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

    async def execute(
        self, command: SetVariantPropertiesCommand
    ) -> SetVariantPropertiesResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        if product.variant.id != command.variant_id:
            raise VariantNotFoundError("Позиция отсутствует в Product.")
        product.set_variant_properties(
            command.virtual, command.downloadable, command.actor_id, self._clock.now()
        )
        await self._repository.save(product)
        return SetVariantPropertiesResultDTO(product.id.uuid, product.revision)
