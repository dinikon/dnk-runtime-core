from src.modules.channels.application.catalog_binding.query.list_publication_binding_candidates.query import (
    ListPublicationBindingCandidatesQuery,
)
from src.modules.channels.application.catalog_binding.queries import BindingQueries
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.query.list_publication_binding_candidates.dto import (
    ListPublicationBindingCandidatesResultDTO,
)


class ListPublicationBindingCandidatesHandler:
    """Сценарий list_publication_binding_candidates на портах внешнего UoW."""

    def __init__(self, queries: BindingQueries, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.queries, self.clock = queries, clock

    async def execute(
        self, query: ListPublicationBindingCandidatesQuery
    ) -> ListPublicationBindingCandidatesResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        page = await self.queries.publication_candidates(
            channel_id=query.channel_id,
            mode=query.mode,
            locale=query.locale,
            search=query.search,
            offset=query.offset,
            limit=query.limit,
        )
        return ListPublicationBindingCandidatesResultDTO(
            page.items, page.occupied_ids, page.total, page.offset, page.limit
        )
