from src.modules.feed_builder.application.publication.command.restore_publication.command import (
    RestorePublicationCommand,
)
from src.modules.feed_builder.application.publication.command.restore_publication.dto import (
    RestorePublicationResultDTO,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogReaderProtocol,
    PublicationSourceNotFoundError,
)
from src.modules.feed_builder.application.publication.participation import (
    load_editable_publication,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class RestorePublicationHandler:
    """Координирует изменение участия через метод агрегата в общем UoW."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        publications: FeedPublicationRepositoryProtocol,
        clock: ClockPort,
        catalog: PublicationCatalogReaderProtocol,
    ) -> None:
        """Принимает только нужные порты процесса."""
        self._feeds, self._publications, self._clock = feeds, publications, clock
        self._catalog = catalog

    async def execute(
        self, command: RestorePublicationCommand
    ) -> RestorePublicationResultDTO:
        """Сохраняет только фактический переход без перезаписи overrides."""

        original = await load_editable_publication(
            self._feeds,
            self._publications,
            command.feed_id,
            command.publication_id,
            command.expected_version,
        )
        result = original.restore_participation(now=self._clock.now())
        if result is not original:
            sources = await self._catalog.read_many((original.product_reference,), "uk")
            if not sources or not sources[0].available:
                raise PublicationSourceNotFoundError("Позиция Catalog недоступна.")
            await self._publications.save(result, original.version)
        return RestorePublicationResultDTO(
            result.id.uuid, result.status.value, result.version.value, result.updated_at
        )
