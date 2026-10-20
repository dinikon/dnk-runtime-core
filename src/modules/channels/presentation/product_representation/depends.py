from src.modules.channels.application.publication_import.consumption import (
    PublicationImportConsumptionService,
)
from src.modules.channels.infrastructure.publication_import.persistence.repository import (
    SqlAlchemyPublicationImportRepository,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.infrastructure.catalog_item.assembly import (
    build_catalog_items_facade,
)
from src.modules.channels.infrastructure.product_representation.adapter.catalog import (
    CatalogAdapter,
)
from src.modules.channels.infrastructure.product_representation.persistence.repository import (
    SqlAlchemyProductRepresentationRepository,
)
from src.modules.channels.infrastructure.product_representation.persistence.publications import (
    SqlAlchemyPublicationCatalogSource,
)
from src.modules.channels.infrastructure.product_representation.persistence.binding_queries import (
    SqlAlchemyBindingQueries,
)
from src.modules.channels.infrastructure.product_representation.persistence.creation_receipts import (
    SqlAlchemyCatalogCreationReceipts,
)
from src.modules.channels.application.product_representation.linking_service import (
    PublicationLinkingService,
)
from src.modules.channels.application.product_representation.command.bind_existing_publication.handler import (
    BindExistingPublicationHandler,
)
from src.modules.channels.application.product_representation.command.unbind_publication.handler import (
    UnbindPublicationHandler,
)
from src.modules.channels.application.product_representation.command.create_catalog_item_from_publication.handler import (
    CreateCatalogItemFromPublicationHandler,
)
from src.modules.channels.application.product_representation.query.preview_catalog_draft.handler import (
    PreviewCatalogDraftHandler,
)
from src.modules.channels.application.product_representation.query.list_catalog_candidates.handler import (
    ListCatalogCandidatesHandler,
)


def get_bind_existing_publication_handler(
    uow: UoWDep, clock: ClockDep, uuid: UuidDep
) -> BindExistingPublicationHandler:
    """Собирает bind_existing_publication на единственной внешней tenant-сессии."""
    repository = SqlAlchemyProductRepresentationRepository(uow.session)
    sources = SqlAlchemyPublicationCatalogSource(uow.session)
    bindings = SqlAlchemyBindingQueries(uow.session)
    linking = PublicationLinkingService(repository, clock, uuid)
    catalog = CatalogAdapter(build_catalog_items_facade(uow.session, clock, uuid))
    return BindExistingPublicationHandler(catalog, sources, bindings, linking)


BindExistingPublicationHandlerDep = Annotated[
    BindExistingPublicationHandler, Depends(get_bind_existing_publication_handler)
]


def get_unbind_publication_handler(
    uow: UoWDep, clock: ClockDep, uuid: UuidDep
) -> UnbindPublicationHandler:
    """Собирает unbind_publication на единственной внешней tenant-сессии."""
    repository = SqlAlchemyProductRepresentationRepository(uow.session)
    sources = SqlAlchemyPublicationCatalogSource(uow.session)
    bindings = SqlAlchemyBindingQueries(uow.session)
    catalog = CatalogAdapter(build_catalog_items_facade(uow.session, clock, uuid))
    return UnbindPublicationHandler(catalog, sources, bindings, repository, clock)


UnbindPublicationHandlerDep = Annotated[
    UnbindPublicationHandler, Depends(get_unbind_publication_handler)
]


def get_create_catalog_item_from_publication_handler(
    uow: UoWDep, clock: ClockDep, uuid: UuidDep
) -> CreateCatalogItemFromPublicationHandler:
    """Собирает create_catalog_item_from_publication на единственной внешней tenant-сессии."""
    repository = SqlAlchemyProductRepresentationRepository(uow.session)
    sources = SqlAlchemyPublicationCatalogSource(uow.session)
    bindings = SqlAlchemyBindingQueries(uow.session)
    receipts = SqlAlchemyCatalogCreationReceipts(uow.session)
    linking = PublicationLinkingService(repository, clock, uuid)
    catalog = CatalogAdapter(build_catalog_items_facade(uow.session, clock, uuid))
    return CreateCatalogItemFromPublicationHandler(
        catalog,
        sources,
        bindings,
        receipts,
        linking,
        clock,
        PublicationImportConsumptionService(
            SqlAlchemyPublicationImportRepository(uow.session),
            SqlAlchemyChannelRepository(uow.session),
            clock,
        ),
    )


CreateCatalogItemFromPublicationHandlerDep = Annotated[
    CreateCatalogItemFromPublicationHandler,
    Depends(get_create_catalog_item_from_publication_handler),
]


def get_preview_catalog_draft_handler(
    uow: UoWDep, clock: ClockDep, uuid: UuidDep
) -> PreviewCatalogDraftHandler:
    """Собирает preview_catalog_draft на единственной внешней tenant-сессии."""
    sources = SqlAlchemyPublicationCatalogSource(uow.session)
    bindings = SqlAlchemyBindingQueries(uow.session)
    catalog = CatalogAdapter(build_catalog_items_facade(uow.session, clock, uuid))
    return PreviewCatalogDraftHandler(sources, catalog, bindings)


PreviewCatalogDraftHandlerDep = Annotated[
    PreviewCatalogDraftHandler, Depends(get_preview_catalog_draft_handler)
]


def get_list_catalog_candidates_handler(
    uow: UoWDep, clock: ClockDep, uuid: UuidDep
) -> ListCatalogCandidatesHandler:
    """Собирает list_catalog_candidates на единственной внешней tenant-сессии."""
    sources = SqlAlchemyPublicationCatalogSource(uow.session)
    bindings = SqlAlchemyBindingQueries(uow.session)
    catalog = CatalogAdapter(build_catalog_items_facade(uow.session, clock, uuid))
    return ListCatalogCandidatesHandler(sources, catalog, bindings)


ListCatalogCandidatesHandlerDep = Annotated[
    ListCatalogCandidatesHandler, Depends(get_list_catalog_candidates_handler)
]
