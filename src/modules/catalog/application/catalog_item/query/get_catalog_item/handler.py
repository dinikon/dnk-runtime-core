from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_item.query.get_catalog_item.query import (
    GetCatalogItemQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    GetCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.error import InvalidCatalogValueError


class GetCatalogItemHandler:
    """Читает batch проекцию без восстановления агрегатов."""

    def __init__(
        self,
        repository: CatalogItemQueryRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает read порт и clock внешней сборки."""
        self._repository = repository
        self._clock = clock

    async def execute(self, query: GetCatalogItemQuery) -> GetCatalogItemResultDTO:
        """Проверяет locale и отдаёт согласованное чтение на едином as_of."""
        LocaleVO(query.locale)
        as_of = query.as_of or self._clock.now()
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise InvalidCatalogValueError("as_of требует timezone.")
        return await self._repository.get(query, as_of)
