from src.modules.catalog.application.category.command.put_category_content.command import (
    PutCategoryContentCommand,
)
from src.modules.catalog.application.category.command.put_category_content.dto import (
    PutCategoryContentResultDTO,
)
from src.modules.catalog.application.category.port.locale_reader import (
    CategoryLocaleReaderPort,
)
from src.modules.catalog.domain.category.error import (
    CategoryLocaleUnavailableError,
    CategoryNotFoundError,
)
from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.domain.category.value_object.translation import (
    CategoryTranslationVO,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class PutCategoryContentHandler:
    def __init__(
        self,
        repository: CategoryRepositoryProtocol,
        locales: CategoryLocaleReaderPort,
        clock: ClockPort,
    ) -> None:
        self._repository, self._locales, self._clock = repository, locales, clock

    async def execute(
        self, command: PutCategoryContentCommand
    ) -> PutCategoryContentResultDTO:
        translation = CategoryTranslationVO(
            CategoryLocaleVO(command.locale), command.name
        )
        if not await self._locales.is_active(translation.locale.value):
            raise CategoryLocaleUnavailableError("Category locale is not active.")
        category = await self._repository.get_for_update(command.category_id)
        if category is None:
            raise CategoryNotFoundError("Category not found.")
        category.set_translation(
            translation, actor_id=command.actor_id, now=self._clock.now()
        )
        await self._repository.save_translation(category, translation.locale)
        return PutCategoryContentResultDTO(
            category.id.uuid,
            translation.locale.value,
            translation.name,
            category.updated_at,
            category.updated_by.uuid,
        )
