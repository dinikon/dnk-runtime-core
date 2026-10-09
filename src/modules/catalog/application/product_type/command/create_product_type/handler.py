from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)

from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.application.product_type.schema_service import (
    ProductSchemaService,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol

from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.product_type.command.create_product_type.command import (
    CreateProductTypeCommand,
)
from src.modules.catalog.application.product_type.command.create_product_type.dto import (
    CreateProductTypeResultDTO,
)


class CreateProductTypeHandler:
    """Координирует create_product_type; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ProductTypeRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
        schemas: ProductSchemaService,
        locales: LocalePort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid
        self._schemas = schemas
        self._locales = locales

    async def execute(
        self, command: CreateProductTypeCommand
    ) -> CreateProductTypeResultDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire(command.tenant_id)
        await self._locales.ensure_active(LocaleVO(command.locale).value)
        await self._schemas.from_links(command.blocks)
        entity = ProductType.create(
            ProductTypeIdVO(self._uuid.new()),
            command.code,
            LocaleVO(command.locale),
            command.label,
            command.blocks,
            command.actor_id,
            self._clock.now(),
        )
        await self._repository.add(entity)
        return CreateProductTypeResultDTO(
            entity.id.uuid, entity.revision, entity.schema_version
        )
