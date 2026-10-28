from src.modules.channels.application.catalog_binding.query.list_catalog_bindings.query import (
    ListCatalogBindingsQuery,
)
from src.modules.channels.application.catalog_binding.queries import BindingQueries
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.query.list_catalog_bindings.dto import (
    ListCatalogBindingsResultDTO,
)


class ListCatalogBindingsHandler:
    """Сценарий list_catalog_bindings на портах внешнего UoW."""

    def __init__(self, queries: BindingQueries, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.queries, self.clock = queries, clock

    async def execute(
        self, query: ListCatalogBindingsQuery
    ) -> ListCatalogBindingsResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        items, total = await self.queries.list(
            catalog_root_id=query.catalog_root_id,
            mode=query.mode,
            channel_id=query.channel_id,
            publication_id=query.publication_id,
            offset=query.offset,
            limit=query.limit,
            locale=query.locale,
            now=self.clock.now(),
        )
        return ListCatalogBindingsResultDTO(items, total, query.offset, query.limit)
