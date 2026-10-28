from src.modules.channels.application.catalog_binding.query.preview_catalog_binding.query import (
    PreviewCatalogBindingQuery,
)
from src.modules.channels.application.catalog_binding.queries import BindingQueries
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.catalog_binding.query.preview_catalog_binding.dto import (
    PreviewCatalogBindingResultDTO,
)


class PreviewCatalogBindingHandler:
    """Сценарий preview_catalog_binding на портах внешнего UoW."""

    def __init__(self, queries: BindingQueries, clock: ClockPort) -> None:
        """Получает конкретный сервис и часы."""
        self.queries, self.clock = queries, clock

    async def execute(
        self, query: PreviewCatalogBindingQuery
    ) -> PreviewCatalogBindingResultDTO:
        """Выполняет отдельный сценарий без вложенных handlers."""
        return PreviewCatalogBindingResultDTO(
            await self.queries.preview(
                channel_id=query.channel_id,
                catalog_root_id=query.catalog_root_id,
                mode=query.mode,
                publication_root_id=query.publication_root_id,
                items=query.items,
                group_id=query.group_id,
                locale=query.locale,
                now=self.clock.now(),
            )
        )
