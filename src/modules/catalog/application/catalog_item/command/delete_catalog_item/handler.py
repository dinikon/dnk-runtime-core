from src.modules.catalog.application.catalog_item.command.delete_catalog_item.command import (
    DeleteCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.usage import CatalogItemUsagePort
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class DeleteCatalogItemHandler:
    """Удаляет проверенный корень без неявных внешних удалений."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        repository: CatalogItemRepositoryProtocol,
        usage: CatalogItemUsagePort,
    ) -> None:
        """Принимает порты проверки и хранения одной семьи."""
        self._mutations = mutations
        self._repository = repository
        self._usage = usage

    async def execute(self, command: DeleteCatalogItemCommand) -> None:
        """Проверяет ревизию, принадлежность корню и использование всех source ID."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        if command.item_id != root.id:
            raise InvalidCatalogValueError("Вариант удаляется явной заменой структуры.")
        root.ensure_deletable(
            bool(
                await self._usage.used_ids(tuple(i.id for i in (root, *root.children)))
            ),
            command.discarded_ids,
        )
        await self._repository.delete(root)
