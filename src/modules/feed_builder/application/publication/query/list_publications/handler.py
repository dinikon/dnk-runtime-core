from src.modules.feed_builder.application.publication.query.list_publications.query import (
    ListPublicationsQuery,
)
from src.modules.feed_builder.application.publication.query.list_publications.dto import (
    ListPublicationsResultDTO,
)
from src.modules.feed_builder.application.publication.port.query_repository import (
    PublicationQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogReaderProtocol,
)
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.publication.read_subjects import (
    enrich_publications,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)


class ListPublicationsHandler:
    """Читает страницу состава без восстановления Feed или Publication."""

    def __init__(
        self,
        feeds: FeedQueryRepositoryProtocol,
        publications: PublicationQueryRepositoryProtocol,
        catalog: PublicationCatalogReaderProtocol,
    ) -> None:
        """Принимает проекции и публичный источник подписей."""
        self._feeds, self._publications, self._catalog = feeds, publications, catalog

    async def execute(self, query: ListPublicationsQuery) -> ListPublicationsResultDTO:
        """Фильтрует и обогащает ограниченную страницу без N+1."""
        if (
            not 1 <= query.limit <= 100
            or query.offset < 0
            or (
                query.status is not None
                and query.status not in {s.value for s in PublicationStatus}
            )
        ):
            raise InvalidPublicationValueError("Неверные параметры страницы.")
        feed = await self._feeds.get_details(FeedIdVO(query.feed_id))
        if feed is None:
            raise FeedNotFoundError("Feed не найден.")
        matched = (
            await self._catalog.search_ids(query.search, query.locale)
            if query.search
            else None
        )
        page = await self._publications.list(
            FeedIdVO(query.feed_id), query.status, matched, query.limit, query.offset
        )
        return ListPublicationsResultDTO(
            feed.id,
            feed.version,
            feed.status,
            await enrich_publications(page.items, self._catalog, query.locale),
            page.total,
            page.counts,
        )
