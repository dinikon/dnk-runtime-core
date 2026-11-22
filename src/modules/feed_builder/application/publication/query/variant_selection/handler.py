from src.modules.feed_builder.application.publication.query.variant_selection.query import (
    VariantSelectionQuery,
)
from src.modules.feed_builder.application.publication.query.variant_selection.dto import (
    VariantSelectionResultDTO,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogReaderProtocol,
)
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedArchivedError,
)


class VariantSelectionHandler:
    """Получает от владельца Catalog фиксированный набор ID текущего семейства."""

    def __init__(
        self,
        feeds: FeedQueryRepositoryProtocol,
        catalog: PublicationCatalogReaderProtocol,
    ) -> None:
        """Принимает только read-side порты."""
        self._feeds, self._catalog = feeds, catalog

    async def execute(self, query: VariantSelectionQuery) -> VariantSelectionResultDTO:
        """Читает ограниченный снимок без создания публикаций."""
        feed = await self._feeds.get_schema(FeedIdVO(query.feed_id))
        if feed is None:
            raise FeedNotFoundError("Feed не найден.")
        if feed.status == "ARCHIVED":
            raise FeedArchivedError("Архивный Feed доступен только для просмотра.")
        return VariantSelectionResultDTO(
            await self._catalog.variant_selection(query.catalog_item_id, query.locale)
        )
