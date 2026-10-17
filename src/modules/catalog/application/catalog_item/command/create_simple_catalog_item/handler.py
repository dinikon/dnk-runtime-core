import logging
from src.modules.catalog.application.catalog_item.command.create_simple_catalog_item.command import (
    CreateSimpleCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.create_simple_catalog_item.dto import (
    CreateSimpleCatalogItemResultDTO,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol

logger = logging.getLogger(__name__)


class CreateSimpleCatalogItemHandler:
    """Координирует создание корня; структуру проверяет Domain."""

    def __init__(
        self,
        repository: CatalogItemRepositoryProtocol,
        lock: CatalogMutationLockPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Подключает порты одной tenant UoW."""
        self._repository = repository
        self._lock = lock
        self._clock = clock
        self._uuid = uuid

    async def execute(
        self, command: CreateSimpleCatalogItemCommand
    ) -> CreateSimpleCatalogItemResultDTO:
        """Создаёт явную модель и сохраняет товар без commit."""
        await self._lock.acquire_reference(command.tenant_id)
        identifier = CatalogItemIdVO(self._uuid.new())
        now = self._clock.now()
        item = CatalogItem.create_simple(
            identifier, command.actor_id, now, command.virtual
        )
        await self._repository.add(item)
        logger.debug(
            "Catalog item creation prepared for external commit",
            extra={
                "event": "catalog.create.prepared",
                "tenant_id": str(command.tenant_id.uuid),
                "item_id": str(item.id.uuid),
            },
        )
        return CreateSimpleCatalogItemResultDTO(item.id.uuid, item.revision)
