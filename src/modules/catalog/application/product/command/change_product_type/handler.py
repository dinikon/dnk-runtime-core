from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.application.product.command.change_product_type.command import (
    ChangeProductTypeCommand,
)
from src.modules.catalog.application.product.command.change_product_type.dto import (
    ChangeProductTypeResultDTO,
)


class ChangeProductTypeHandler:
    """Координирует change_product_type; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        schemas: ProductSchemaService,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._schemas = schemas

    async def execute(
        self, command: ChangeProductTypeCommand
    ) -> ChangeProductTypeResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        product.change_type(
            await self._schemas.get(command.product_type_id),
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(product)
        return ChangeProductTypeResultDTO(product.id.uuid, product.revision)
