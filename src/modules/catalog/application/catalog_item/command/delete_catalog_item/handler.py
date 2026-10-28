from src.modules.catalog.application.catalog_item.port.publication_usage import (
    CatalogPublicationUsagePort,
)
from src.modules.catalog.application.catalog_item.command.delete_catalog_item.command import (
    DeleteCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)


class DeleteCatalogItemHandler:
    """Удаляет проверенный корень без неявных внешних удалений."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        repository: CatalogItemRepositoryProtocol,
        usage: CatalogPublicationUsagePort,
    ) -> None:
        """Принимает порты проверки и хранения одного товара."""
        self._mutations = mutations
        self._repository = repository
        self._usage = usage

    async def execute(self, command: DeleteCatalogItemCommand) -> None:
        """Загружает товар под блокировкой и удаляет в общей транзакции."""
        item = await self._mutations.load(command.tenant_id, command.item_id)
        item.ensure_deletable(in_use=await self._usage.used(item.id.uuid))
        await self._repository.delete(item)
