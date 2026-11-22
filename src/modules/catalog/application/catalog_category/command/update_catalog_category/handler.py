from src.modules.catalog.domain.catalog_category.repository import (
    CatalogCategoryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_category.command.update_catalog_category.command import (
    UpdateCatalogCategoryCommand,
)
from src.modules.catalog.application.catalog_category.command.update_catalog_category.dto import (
    UpdateCatalogCategoryResultDTO,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.domain.value_object.locale import LocaleVO


class UpdateCatalogCategoryHandler:
    """Применяет перенос узла и изменения его переводов."""

    def __init__(
        self, repository: CatalogCategoryRepositoryProtocol, locales: LocalePort
    ) -> None:
        """Принимает зависимости текущего сценария."""
        self.repository = repository
        self.locales = locales

    async def execute(
        self, command: UpdateCatalogCategoryCommand
    ) -> UpdateCatalogCategoryResultDTO:
        """Изменяет переводы и положение категории за одну транзакцию."""
        await self.repository.lock_tree(command.tenant_id)
        category = await self.repository.get(command.category_id)
        if command.move:
            category.move(command.parent_id, await self.repository.parents())
        for code, name in command.translations.items():
            locale = LocaleVO(code)
            await self.locales.ensure_active(code)
            category.translate(locale, name)
        await self.repository.save(category)
        return UpdateCatalogCategoryResultDTO(category.id.uuid)
