from src.modules.catalog.application.catalog_item.query.list_catalog_variants.query import (
    ListCatalogVariantsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_variants.dto import (
    ListCatalogVariantsResultDTO,
)
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort


class ListCatalogVariantsHandler:
    """Читает конкретную проекцию через Application-порт без Aggregate restore."""

    def __init__(
        self, repository: CatalogItemQueryRepositoryProtocol, clock: ClockPort
    ) -> None:
        """Принимает read порт и часы согласованного as_of."""
        self._repository, self._clock = repository, clock

    async def execute(
        self, query: ListCatalogVariantsQuery
    ) -> ListCatalogVariantsResultDTO:
        """Проверяет locale и возвращает результат конкретного сценария."""
        LocaleVO(query.locale)
        return await self._repository.list_variants(
            query, query.as_of or self._clock.now()
        )
