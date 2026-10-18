from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
import logging
from src.modules.catalog.application.catalog_item.command.create_catalog_item.command import (
    CreateCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.dto import (
    CreateCatalogItemResultDTO,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol

logger = logging.getLogger(__name__)


class CreateCatalogItemHandler:
    """Координирует создание корня; структуру проверяет Domain."""

    def __init__(
        self,
        repository: CatalogItemRepositoryProtocol,
        schemas: CatalogItemContentSchemaPort,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Подключает порты одной tenant UoW."""
        self._repository = repository
        self._schemas = schemas
        self._clock = clock
        self._uuid = uuid

    async def execute(
        self, command: CreateCatalogItemCommand
    ) -> CreateCatalogItemResultDTO:
        """Создаёт явную модель и сохраняет товар без commit."""
        schema = await self._schemas.get_by_code(command.product_type_code)
        identifier = CatalogItemIdVO(self._uuid.new())
        now = self._clock.now()
        item = CatalogItem.create(
            identifier, command.actor_id, now, schema.id, command.virtual
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
        return CreateCatalogItemResultDTO(item.id.uuid)
