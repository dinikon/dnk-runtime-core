import logging
from src.modules.catalog.application.catalog_item.command.create_catalog_item.command import (
    CreateCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.dto import (
    CreateCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)

logger = logging.getLogger(__name__)


class CreateCatalogItemHandler:
    """Создаёт пустой или заполненный самостоятельный товар одним сценарием Catalog."""

    def __init__(
        self,
        repository: CatalogItemRepositoryProtocol,
        creation: CatalogItemCreationService,
    ) -> None:
        """Принимает сервис подготовки и репозиторий одного внешнего UoW."""
        self.repository, self.creation = repository, creation

    async def execute(
        self, command: CreateCatalogItemCommand
    ) -> CreateCatalogItemResultDTO:
        """Сохраняет только полностью подготовленный агрегат без собственного commit."""
        item = await self.creation.prepare(
            command.tenant_id, command.actor_id, command.product
        )
        await self.repository.add(item)
        logger.debug(
            "Catalog item creation prepared for external commit",
            extra={
                "event": "catalog.create.prepared",
                "tenant_id": str(command.tenant_id.uuid),
                "item_id": str(item.id.uuid),
            },
        )
        return CreateCatalogItemResultDTO(item.id.uuid)
