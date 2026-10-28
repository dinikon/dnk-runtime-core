from src.modules.channels.application.catalog_binding.query.get_catalog_binding.query import (
    GetCatalogBindingQuery,
)
from src.modules.channels.application.catalog_binding.queries import BindingQueries
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.query.get_catalog_binding.dto import (
    GetCatalogBindingResultDTO,
)


class GetCatalogBindingHandler:
    """Сценарий get_catalog_binding на портах внешнего UoW."""

    def __init__(self, queries: BindingQueries, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.queries, self.clock = queries, clock

    async def execute(
        self, query: GetCatalogBindingQuery
    ) -> GetCatalogBindingResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        return GetCatalogBindingResultDTO(
            await self.queries.get(
                query.channel_id, query.group_id, query.locale, self.clock.now()
            )
        )
