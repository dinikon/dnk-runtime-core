from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.command import (
    LockCatalogItemForBindingCommand,
)
from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.dto import (
    LockCatalogItemForBindingResultDTO,
)

from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)


class LockCatalogItemForBindingHandler:
    """Публично сериализует binding и удаление владельцем Catalog item."""

    def __init__(self, mutations: CatalogItemMutationService) -> None:
        """Получает загрузку под собственной item-блокировкой Catalog."""
        self.mutations = mutations

    async def execute(
        self, command: LockCatalogItemForBindingCommand
    ) -> LockCatalogItemForBindingResultDTO:
        """Возвращает только разрешённую проекцию, не внутренний агрегат."""
        item = await self.mutations.load(command.tenant_id, command.item_id)
        return LockCatalogItemForBindingResultDTO(item.id.uuid, item.status.value)
