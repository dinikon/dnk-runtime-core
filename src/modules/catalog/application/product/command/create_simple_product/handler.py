from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO

from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol

from src.modules.catalog.application.product.command.create_simple_product.command import (
    CreateSimpleProductCommand,
)
from src.modules.catalog.application.product.command.create_simple_product.dto import (
    CreateSimpleProductResultDTO,
)


class CreateSimpleProductHandler:
    """Координирует create_simple_product; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        schemas: ProductSchemaService,
        types: ProductTypeRepositoryProtocol,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid
        self._schemas = schemas
        self._types = types

    async def execute(
        self, command: CreateSimpleProductCommand
    ) -> CreateSimpleProductResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        type_id = command.product_type_id or await self._types.get_default_id()
        schema = await self._schemas.get(type_id)
        product = Product.create(
            ProductIdVO(self._uuid.new()),
            schema,
            VariantIdVO(self._uuid.new()),
            command.virtual,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(product)
        return CreateSimpleProductResultDTO(
            product.id.uuid, product.revision, product.variant.id.uuid
        )
