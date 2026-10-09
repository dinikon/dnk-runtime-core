from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.domain.product.value_object.schema import ProductSchemaSnapshot
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort

from src.modules.catalog.application.product_type.command.replace_product_type_schema.command import (
    ReplaceProductTypeSchemaCommand,
)
from src.modules.catalog.application.product_type.command.replace_product_type_schema.dto import (
    ReplaceProductTypeSchemaResultDTO,
)


class ReplaceProductTypeSchemaHandler:
    """Координирует replace_product_type_schema; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        schemas: ProductSchemaService,
        products: ProductRepositoryProtocol,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._schemas = schemas
        self._products = products

    async def execute(
        self, command: ReplaceProductTypeSchemaCommand
    ) -> ReplaceProductTypeSchemaResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        entity = await self._repository.get(command.product_type_id)
        entity.ensure_revision(command.expected_revision)
        blocks = await self._schemas.from_links(command.blocks)
        candidate = ProductSchemaSnapshot(entity.id, entity.schema_version + 1, blocks)
        for product in await self._products.get_by_type(entity.id):
            product.validate_content(candidate)
        entity.replace_schema(
            command.blocks,
            command.expected_schema_version,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.save(entity)
        return ReplaceProductTypeSchemaResultDTO(
            entity.id.uuid, entity.revision, entity.schema_version
        )
