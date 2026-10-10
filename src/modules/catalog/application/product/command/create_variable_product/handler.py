from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.product.structure_service import (
    ProductStructureService,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
)
from src.modules.catalog.application.product.command.create_variable_product.dto import (
    CreateVariableProductResultDTO,
)


class CreateVariableProductHandler:
    """Координирует create_variable_product; весь переход состояния выполняет Product."""

    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        schemas: ProductSchemaService,
        structures: ProductStructureService,
        uuid: UUIdGeneratorProtocol,
        types: ProductTypeRepositoryProtocol,
    ) -> None:
        """Принимает необходимые порты и координатор снимков на общем UoW."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._schemas = schemas
        self._structures = structures
        self._uuid = uuid
        self._types = types

    async def execute(
        self, command: CreateVariableProductCommand
    ) -> CreateVariableProductResultDTO:
        """Применяет полную структуру и сохраняет агрегат без самостоятельного commit."""
        await self._lock.acquire(command.tenant_id)
        schema = await self._schemas.get(
            command.product_type_id or await self._types.get_default_id()
        )
        structure, definitions = await self._structures.prepare(command.structure)
        product = Product.create_variable(
            ProductIdVO(self._uuid.new()),
            schema,
            structure,
            definitions,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(product)
        return CreateVariableProductResultDTO(product.id.uuid, product.revision)
