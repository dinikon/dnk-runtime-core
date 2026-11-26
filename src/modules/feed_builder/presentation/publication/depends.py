from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.feed_builder.presentation.feed.depends import (
    FeedSettingsRepositoryDep,
    FeedQueryRepositoryDep,
)
from src.modules.feed_builder.domain.publication.repository import (
    FeedPublicationRepositoryProtocol,
)
from src.modules.feed_builder.application.publication.port.query_repository import (
    PublicationQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogReaderProtocol,
)
from src.modules.feed_builder.infrastructure.publication.persistence.repository import (
    SqlAlchemyFeedPublicationRepository,
)
from src.modules.feed_builder.infrastructure.publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)
from src.modules.feed_builder.infrastructure.publication.catalog.subjects import (
    CatalogPublicationReader,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.publication_reader import (
    SqlAlchemyCatalogPublicationReader,
)
from src.modules.feed_builder.application.publication.command.add_catalog_items.handler import (
    AddCatalogItemsHandler,
)
from src.modules.feed_builder.application.publication.command.change_publication_status.handler import (
    ChangePublicationStatusHandler,
)
from src.modules.feed_builder.application.publication.command.remove_publication.handler import (
    RemovePublicationHandler,
)
from src.modules.feed_builder.application.publication.command.restore_publication.handler import (
    RestorePublicationHandler,
)
from src.modules.feed_builder.application.publication.query.list_publications.handler import (
    ListPublicationsHandler,
)
from src.modules.feed_builder.application.publication.query.get_publication.handler import (
    GetPublicationHandler,
)
from src.modules.feed_builder.application.publication.query.variant_selection.handler import (
    VariantSelectionHandler,
)


def get_publications(uow: UoWDep) -> FeedPublicationRepositoryProtocol:
    """Собирает write repository на той же сессии, что Feed."""
    return SqlAlchemyFeedPublicationRepository(uow.session)


def get_publication_queries(uow: UoWDep) -> PublicationQueryRepositoryProtocol:
    """Собирает независимое чтение проекций."""
    return SqlAlchemyPublicationQueryRepository(uow.session)


def get_publication_catalog(uow: UoWDep) -> PublicationCatalogReaderProtocol:
    """Соединяет публичный owner-reader и FeedBuilder адаптер без отдельного UoW."""
    return CatalogPublicationReader(SqlAlchemyCatalogPublicationReader(uow.session))


PublicationsDep = Annotated[
    FeedPublicationRepositoryProtocol, Depends(get_publications)
]
PublicationQueriesDep = Annotated[
    PublicationQueryRepositoryProtocol, Depends(get_publication_queries)
]
PublicationCatalogDep = Annotated[
    PublicationCatalogReaderProtocol, Depends(get_publication_catalog)
]


def get_add_catalog_items_handler(
    feeds: FeedSettingsRepositoryDep,
    publications: PublicationsDep,
    catalog: PublicationCatalogDep,
    clock: ClockDep,
    identifiers: UuidDep,
) -> AddCatalogItemsHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return AddCatalogItemsHandler(feeds, publications, catalog, clock, identifiers)


AddCatalogItemsHandlerDep = Annotated[
    AddCatalogItemsHandler, Depends(get_add_catalog_items_handler)
]


def get_change_publication_status_handler(
    feeds: FeedSettingsRepositoryDep, publications: PublicationsDep, clock: ClockDep
) -> ChangePublicationStatusHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return ChangePublicationStatusHandler(feeds, publications, clock)


ChangePublicationStatusHandlerDep = Annotated[
    ChangePublicationStatusHandler, Depends(get_change_publication_status_handler)
]


def get_remove_publication_handler(
    feeds: FeedSettingsRepositoryDep, publications: PublicationsDep, clock: ClockDep
) -> RemovePublicationHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return RemovePublicationHandler(feeds, publications, clock)


RemovePublicationHandlerDep = Annotated[
    RemovePublicationHandler, Depends(get_remove_publication_handler)
]


def get_restore_publication_handler(
    feeds: FeedSettingsRepositoryDep,
    publications: PublicationsDep,
    clock: ClockDep,
    catalog: PublicationCatalogDep,
) -> RestorePublicationHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return RestorePublicationHandler(feeds, publications, clock, catalog)


RestorePublicationHandlerDep = Annotated[
    RestorePublicationHandler, Depends(get_restore_publication_handler)
]


def get_list_publications_handler(
    feeds: FeedQueryRepositoryDep,
    publications: PublicationQueriesDep,
    catalog: PublicationCatalogDep,
) -> ListPublicationsHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return ListPublicationsHandler(feeds, publications, catalog)


ListPublicationsHandlerDep = Annotated[
    ListPublicationsHandler, Depends(get_list_publications_handler)
]


def get_get_publication_handler(
    feeds: FeedQueryRepositoryDep,
    publications: PublicationQueriesDep,
    catalog: PublicationCatalogDep,
) -> GetPublicationHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return GetPublicationHandler(feeds, publications, catalog)


GetPublicationHandlerDep = Annotated[
    GetPublicationHandler, Depends(get_get_publication_handler)
]


def get_variant_selection_handler(
    feeds: FeedQueryRepositoryDep, catalog: PublicationCatalogDep
) -> VariantSelectionHandler:
    """Собирает конкретный сценарий из портов общей tenant-транзакции."""
    return VariantSelectionHandler(feeds, catalog)


VariantSelectionHandlerDep = Annotated[
    VariantSelectionHandler, Depends(get_variant_selection_handler)
]
