from src.modules.feed_builder.application.publication.command.add_catalog_items.command import (
    AddCatalogItemsCommand,
)
from src.modules.feed_builder.application.publication.command.add_catalog_items.dto import (
    AddCatalogItemsResultDTO,
    AddedPublicationDTO,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogReaderProtocol,
    PublicationSourceNotFoundError,
)
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.policy.participation import (
    PublicationParticipationPolicy,
)
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class AddCatalogItemsHandler:
    """Атомарно создаёт недостающие привязки, сохраняя существующие статусы/overrides."""

    def __init__(
        self,
        feeds: FeedRepositoryProtocol,
        publications: FeedPublicationRepositoryProtocol,
        catalog: PublicationCatalogReaderProtocol,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает необходимые порты общего UoW без сессии и commit."""
        (
            self._feeds,
            self._publications,
            self._catalog,
            self._clock,
            self._identifiers,
        ) = (feeds, publications, catalog, clock, identifiers)

    async def execute(
        self, command: AddCatalogItemsCommand
    ) -> AddCatalogItemsResultDTO:
        """Сериализует изменения состава блокировкой Feed и проверяет весь пакет до записи."""
        if not 1 <= len(command.item_references) <= 100:
            raise InvalidPublicationValueError("Выберите от 1 до 100 позиций.")
        feed = await self._feeds.get_for_update(command.feed_id)
        PublicationParticipationPolicy.ensure_editable(
            feed, FeedVersionVO(command.expected_feed_version)
        )
        references = tuple(dict.fromkeys(command.item_references))
        available = {
            s.reference
            for s in await self._catalog.read_many(references, "uk")
            if s.available
        }
        if any(r not in available for r in references):
            raise PublicationSourceNotFoundError(
                "Одна из выбранных позиций недоступна или не принадлежит родителю."
            )
        existing = {
            p.product_reference: p
            for p in await self._publications.find(command.feed_id, references)
        }
        now = self._clock.now()
        created = tuple(
            FeedPublication.create(
                identifier=FeedPublicationIdVO.from_value(self._identifiers.new()),
                feed_id=command.feed_id,
                product_reference=r,
                now=now,
            )
            for r in references
            if r not in existing
        )
        await self._publications.add_many(created)
        combined = {**existing, **{p.product_reference: p for p in created}}
        return AddCatalogItemsResultDTO(
            feed.id.uuid,
            feed.version.value,
            tuple(
                AddedPublicationDTO(
                    combined[r].id.uuid,
                    r.catalog_item_id.uuid,
                    r.catalog_variant_id.uuid if r.catalog_variant_id else None,
                    combined[r].status.value,
                    combined[r].version.value,
                    "EXISTING" if r in existing else "CREATED",
                )
                for r in references
            ),
        )
