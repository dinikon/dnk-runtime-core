from src.modules.catalog.domain.catalog_category.repository import (
    CatalogCategoryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_category.command.create_catalog_category.command import (
    CreateCatalogCategoryCommand,
)
from src.modules.catalog.application.catalog_category.command.create_catalog_category.dto import (
    CreateCatalogCategoryResultDTO,
)
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.catalog_category.aggregate import CatalogCategory


class CreateCatalogCategoryHandler:
    """Создаёт категорию и проверяет положение нового узла в дереве."""

    def __init__(
        self,
        repository: CatalogCategoryRepositoryProtocol,
        locales: LocalePort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает зависимости текущего сценария."""
        self.repository = repository
        self.locales = locales
        self.uuid = uuid

    async def execute(
        self, command: CreateCatalogCategoryCommand
    ) -> CreateCatalogCategoryResultDTO:
        """Создаёт узел дерева на исходном языке."""
        await self.repository.lock_tree(command.tenant_id)
        await self.locales.ensure_active(command.source_locale.value)
        category = CatalogCategory.create(
            CatalogCategoryIdVO(self.uuid.new()),
            None,
            command.source_locale,
            command.name,
        )
        if command.parent_id is not None:
            category.move(command.parent_id, await self.repository.parents())
        await self.repository.add(category)
        return CreateCatalogCategoryResultDTO(category.id.uuid)
