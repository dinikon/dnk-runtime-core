from src.modules.catalog.domain.catalog_category.repository import (
    CatalogCategoryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_category.command.delete_catalog_category.command import (
    DeleteCatalogCategoryCommand,
)


class DeleteCatalogCategoryHandler:
    """Удаляет свободную категорию после проверки назначений и дочерних узлов."""

    def __init__(self, repository: CatalogCategoryRepositoryProtocol) -> None:
        """Принимает зависимости текущего сценария."""
        self.repository = repository

    async def execute(self, command: DeleteCatalogCategoryCommand) -> None:
        """Удаляет свободный узел дерева."""
        await self.repository.lock_tree(command.tenant_id)
        category = await self.repository.get(command.category_id)
        parents = await self.repository.parents()
        category.ensure_removable(
            has_children=category.id in parents.values(),
            has_items=await self.repository.has_items(category.id),
        )
        await self.repository.delete(category)
