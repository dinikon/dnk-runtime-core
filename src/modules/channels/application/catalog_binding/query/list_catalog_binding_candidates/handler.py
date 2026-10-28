from src.modules.channels.application.catalog_binding.query.list_catalog_binding_candidates.query import (
    ListCatalogBindingCandidatesQuery,
)
from src.modules.channels.application.catalog_binding.queries import BindingQueries
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.query.list_catalog_binding_candidates.dto import (
    ListCatalogBindingCandidatesResultDTO,
)


class ListCatalogBindingCandidatesHandler:
    """Сценарий list_catalog_binding_candidates на портах внешнего UoW."""

    def __init__(self, queries: BindingQueries, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.queries, self.clock = queries, clock

    async def execute(
        self, query: ListCatalogBindingCandidatesQuery
    ) -> ListCatalogBindingCandidatesResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        page = await self.queries.catalog_candidates(
            tenant_id=query.tenant_id,
            channel_id=query.channel_id,
            mode=query.mode,
            locale=query.locale,
            search=query.search,
            offset=query.offset,
            limit=query.limit,
            now=self.clock.now(),
        )
        return ListCatalogBindingCandidatesResultDTO(
            page.items, page.occupied_ids, page.total, page.offset, page.limit
        )
