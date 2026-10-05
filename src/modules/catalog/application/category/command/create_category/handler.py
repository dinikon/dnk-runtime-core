from src.modules.catalog.application.category.command.create_category.command import (
    CreateCategoryCommand,
)
from src.modules.catalog.application.category.command.create_category.dto import (
    CreateCategoryResultDTO,
)
from src.modules.catalog.application.category.port.locale_reader import (
    CategoryLocaleReaderPort,
)
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.error import (
    CategoryLocaleUnavailableError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.domain.category.value_object.translation import (
    CategoryTranslationVO,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class CreateCategoryHandler:
    def __init__(
        self,
        repository: CategoryRepositoryProtocol,
        locales: CategoryLocaleReaderPort,
        clock: ClockPort,
        uuids: UUIdGeneratorProtocol,
    ) -> None:
        self._repository, self._locales, self._clock, self._uuids = (
            repository,
            locales,
            clock,
            uuids,
        )

    async def execute(self, command: CreateCategoryCommand) -> CreateCategoryResultDTO:
        translations = tuple(
            CategoryTranslationVO(CategoryLocaleVO(item.locale), item.name)
            for item in command.translations
        )
        category = Category.create(
            category_id=CategoryIdVO.from_value(self._uuids.new()),
            parent_id=(
                CategoryIdVO.from_value(command.parent_id)
                if command.parent_id
                else None
            ),
            translations=translations,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        for locale in category.translations:
            if not await self._locales.is_active(locale):
                raise CategoryLocaleUnavailableError("Category locale is not active.")
        await self._repository.lock_tree(command.tenant_id)
        if category.parent_id is not None and not await self._repository.exists(
            category.parent_id
        ):
            raise CategoryNotFoundError("Parent category not found.")
        await self._repository.add(category)
        return CreateCategoryResultDTO(
            category.id.uuid,
            category.parent_id.uuid if category.parent_id else None,
            tuple(sorted(category.translations)),
            category.created_at,
            category.updated_at,
            category.created_by.uuid,
            category.updated_by.uuid,
        )
