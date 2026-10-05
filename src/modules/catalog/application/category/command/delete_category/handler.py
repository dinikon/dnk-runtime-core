from src.modules.catalog.application.category.command.delete_category.command import (
    DeleteCategoryCommand,
)
from src.modules.catalog.application.category.command.delete_category.dto import (
    DeleteCategoryResultDTO,
)
from src.modules.catalog.domain.category.error import (
    CategoryInUseError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol


class DeleteCategoryHandler:
    def __init__(self, repository: CategoryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, command: DeleteCategoryCommand) -> DeleteCategoryResultDTO:
        await self._repository.lock_tree(command.tenant_id)
        category = await self._repository.get_for_update(command.category_id)
        if category is None:
            raise CategoryNotFoundError("Category not found.")
        if await self._repository.has_children_or_products(command.category_id):
            raise CategoryInUseError("Category has children or products.")
        await self._repository.delete(command.category_id)
        return DeleteCategoryResultDTO(category.id.uuid)
