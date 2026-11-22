from src.modules.catalog.domain.catalog_category.repository import (
    CatalogCategoryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_category.command.set_default_catalog_category.command import (
    SetDefaultCatalogCategoryCommand,
)
from src.modules.catalog.application.catalog_category.command.set_default_catalog_category.dto import (
    SetDefaultCatalogCategoryResultDTO,
)


class SetDefaultCatalogCategoryHandler:
    """Меняет категорию по умолчанию для новых карточек каталога."""

    def __init__(self, repository: CatalogCategoryRepositoryProtocol) -> None:
        """Принимает зависимости текущего сценария."""
        self.repository = repository

    async def execute(
        self, command: SetDefaultCatalogCategoryCommand
    ) -> SetDefaultCatalogCategoryResultDTO:
        """Выбирает категорию по умолчанию для новых товаров."""
        await self.repository.lock_tree(command.tenant_id)
        category = await self.repository.get(command.category_id)
        await self.repository.set_default(category.id)
        return SetDefaultCatalogCategoryResultDTO(category.id.uuid)
