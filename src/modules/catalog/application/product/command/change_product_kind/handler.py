from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.product.structure_service import (
    ProductStructureService,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.product.command.change_product_kind.command import (
    ChangeProductKindCommand,
)
from src.modules.catalog.application.product.command.change_product_kind.dto import (
    ChangeProductKindResultDTO,
)


class ChangeProductKindHandler:
    """Координирует change_product_kind; весь переход состояния выполняет Product."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        schemas: ProductSchemaService,
        structures: ProductStructureService,
    ) -> None:
        """Принимает необходимые порты и координатор снимков на общем UoW."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._schemas = schemas
        self._structures = structures

    async def execute(
        self, command: ChangeProductKindCommand
    ) -> ChangeProductKindResultDTO:
        """Применяет полную структуру и сохраняет агрегат без самостоятельного commit."""
        await self._lock.acquire(command.tenant_id)
        product = await self._repository.get(command.product_id)
        product.ensure_revision(command.expected_revision)
        schema = await self._schemas.get(product.product_type_id)
        structure, definitions = await self._structures.prepare(
            command.structure, product
        )
        product.change_kind(
            command.kind,
            structure,
            definitions,
            schema,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(product)
        return ChangeProductKindResultDTO(product.id.uuid, product.revision)
