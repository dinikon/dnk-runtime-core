from src.modules.channels.infrastructure.catalog_binding.query_repository import (
    SqlAlchemyCatalogBindingQueryRepository,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.depends import tenant_id_from_context
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.channels.infrastructure.catalog_binding.catalog import (
    CatalogBindingGateway,
)
from src.modules.channels.infrastructure.catalog_binding.repository import (
    SqlAlchemyCatalogBindingRepository,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.application.catalog_binding.views import BindingViews
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.channels.application.catalog_binding.queries import BindingQueries
from src.modules.channels.application.catalog_binding.command.create_catalog_binding.handler import (
    CreateCatalogBindingHandler,
)
from src.modules.channels.application.catalog_binding.command.update_catalog_binding.handler import (
    UpdateCatalogBindingHandler,
)
from src.modules.channels.application.catalog_binding.command.delete_catalog_binding.handler import (
    DeleteCatalogBindingHandler,
)
from src.modules.channels.application.catalog_binding.query.get_catalog_binding.handler import (
    GetCatalogBindingHandler,
)
from src.modules.channels.application.catalog_binding.query.list_catalog_bindings.handler import (
    ListCatalogBindingsHandler,
)
from src.modules.channels.application.catalog_binding.query.preview_catalog_binding.handler import (
    PreviewCatalogBindingHandler,
)
from src.modules.channels.application.catalog_binding.query.list_catalog_binding_candidates.handler import (
    ListCatalogBindingCandidatesHandler,
)
from src.modules.channels.application.catalog_binding.query.list_publication_binding_candidates.handler import (
    ListPublicationBindingCandidatesHandler,
)


@dataclass(slots=True)
class BindingRuntime:
    """Сервисы одной внешней tenant-сессии."""

    writes: BindingWrites
    queries: BindingQueries


def get_binding_runtime(
    uow: UoWDep, uuid: UuidDep, context: AuthenticatedRequestContextDep
) -> BindingRuntime:
    """Собирает взаимные порты без вложенных UoW."""
    read = SqlAlchemyCatalogBindingQueryRepository(uow.session)
    catalog = CatalogBindingGateway(
        CatalogBindingsFacade(
            SqlAlchemyCatalogItemQueryRepository(uow.session),
            PostgresCatalogMutationLock(uow.session),
        )
    )
    views = BindingViews(catalog, read)
    return BindingRuntime(
        BindingWrites(
            catalog,
            SqlAlchemyCatalogBindingRepository(uow.session),
            SqlAlchemyChannelRepository(uow.session, tenant_id_from_context(context)),
            views,
            uuid,
        ),
        BindingQueries(read, catalog, views),
    )


BindingRuntimeDep = Annotated[BindingRuntime, Depends(get_binding_runtime)]


def get_create_catalog_binding_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> CreateCatalogBindingHandler:
    """Собирает отдельный сценарий create_catalog_binding."""
    return CreateCatalogBindingHandler(runtime.writes, clock)


CreateCatalogBindingHandlerDep = Annotated[
    CreateCatalogBindingHandler, Depends(get_create_catalog_binding_handler)
]


def get_update_catalog_binding_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> UpdateCatalogBindingHandler:
    """Собирает отдельный сценарий update_catalog_binding."""
    return UpdateCatalogBindingHandler(runtime.writes, clock)


UpdateCatalogBindingHandlerDep = Annotated[
    UpdateCatalogBindingHandler, Depends(get_update_catalog_binding_handler)
]


def get_delete_catalog_binding_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> DeleteCatalogBindingHandler:
    """Собирает отдельный сценарий delete_catalog_binding."""
    return DeleteCatalogBindingHandler(runtime.writes, clock)


DeleteCatalogBindingHandlerDep = Annotated[
    DeleteCatalogBindingHandler, Depends(get_delete_catalog_binding_handler)
]


def get_get_catalog_binding_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> GetCatalogBindingHandler:
    """Собирает отдельный сценарий get_catalog_binding."""
    return GetCatalogBindingHandler(runtime.queries, clock)


GetCatalogBindingHandlerDep = Annotated[
    GetCatalogBindingHandler, Depends(get_get_catalog_binding_handler)
]


def get_list_catalog_bindings_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> ListCatalogBindingsHandler:
    """Собирает отдельный сценарий list_catalog_bindings."""
    return ListCatalogBindingsHandler(runtime.queries, clock)


ListCatalogBindingsHandlerDep = Annotated[
    ListCatalogBindingsHandler, Depends(get_list_catalog_bindings_handler)
]


def get_preview_catalog_binding_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> PreviewCatalogBindingHandler:
    """Собирает отдельный сценарий preview_catalog_binding."""
    return PreviewCatalogBindingHandler(runtime.queries, clock)


PreviewCatalogBindingHandlerDep = Annotated[
    PreviewCatalogBindingHandler, Depends(get_preview_catalog_binding_handler)
]


def get_list_catalog_binding_candidates_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> ListCatalogBindingCandidatesHandler:
    """Собирает отдельный сценарий list_catalog_binding_candidates."""
    return ListCatalogBindingCandidatesHandler(runtime.queries, clock)


ListCatalogBindingCandidatesHandlerDep = Annotated[
    ListCatalogBindingCandidatesHandler,
    Depends(get_list_catalog_binding_candidates_handler),
]


def get_list_publication_binding_candidates_handler(
    runtime: BindingRuntimeDep, clock: ClockDep
) -> ListPublicationBindingCandidatesHandler:
    """Собирает отдельный сценарий list_publication_binding_candidates."""
    return ListPublicationBindingCandidatesHandler(runtime.queries, clock)


ListPublicationBindingCandidatesHandlerDep = Annotated[
    ListPublicationBindingCandidatesHandler,
    Depends(get_list_publication_binding_candidates_handler),
]
