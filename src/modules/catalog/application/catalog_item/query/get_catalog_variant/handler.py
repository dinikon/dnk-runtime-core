from src.modules.catalog.application.catalog_item.query.get_catalog_variant.query import (
    GetCatalogVariantQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant.dto import (
    GetCatalogVariantResultDTO,
)
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.shared.domain.time.clock_port import ClockPort


class GetCatalogVariantHandler:
    """Читает конкретную проекцию через Application-порт без Aggregate restore."""

    def __init__(
        self, repository: CatalogItemQueryRepositoryProtocol, clock: ClockPort
    ) -> None:
        """Принимает read порт и часы согласованного as_of."""
        self._repository, self._clock = repository, clock

    async def execute(
        self, query: GetCatalogVariantQuery
    ) -> GetCatalogVariantResultDTO:
        """Проверяет locale и возвращает результат конкретного сценария."""
        LocaleVO(query.locale)
        return await self._repository.get_variant(
            query, query.as_of or self._clock.now()
        )
