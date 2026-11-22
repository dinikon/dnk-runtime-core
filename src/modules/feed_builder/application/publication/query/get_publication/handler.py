from src.modules.feed_builder.application.publication.query.get_publication.query import (
    GetPublicationQuery,
)
from src.modules.feed_builder.application.publication.query.get_publication.dto import (
    GetPublicationResultDTO,
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
from src.modules.feed_builder.domain.publication.error import PublicationNotFoundError


class GetPublicationHandler:
    """Читает карточку через проекции без Domain restore."""

    def __init__(
        self,
        feeds: FeedQueryRepositoryProtocol,
        publications: PublicationQueryRepositoryProtocol,
        catalog: PublicationCatalogReaderProtocol,
    ) -> None:
        """Принимает read-side порты общего tenant."""
        self._feeds, self._publications, self._catalog = feeds, publications, catalog

    async def execute(self, query: GetPublicationQuery) -> GetPublicationResultDTO:
        """Сохраняет публикацию видимой при удалении исходной позиции."""
        record = await self._publications.get(query.publication_id)
        if record is None:
            raise PublicationNotFoundError("Публикация не найдена.")
        feed = await self._feeds.get_schema(FeedIdVO(record.feed_id))
        if feed is None:
            raise PublicationNotFoundError("Feed не найден.")
        return GetPublicationResultDTO(
            (await enrich_publications((record,), self._catalog, query.locale))[0],
            feed.version,
            feed.status,
        )
