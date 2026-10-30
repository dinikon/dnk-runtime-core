from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.channels.application.product_representation.query.preview_representation.handler import (
    PreviewRepresentationHandler,
)
from src.modules.channels.application.product_representation.service.builder import (
    RepresentationBuilder,
)
from src.modules.channels.infrastructure.catalog_binding.query_repository import (
    SqlAlchemyCatalogBindingQueryRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.product_representation.catalog import (
    RepresentationCatalogGateway,
)
from src.modules.channels.infrastructure.product_representation.query_repository import (
    SqlAlchemyRepresentationQueryRepository,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.depends import get_platforms
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_preview_representation_handler(
    uow: UoWDep,
    clock: ClockDep,
    platforms: Annotated[InstalledPlatforms, Depends(get_platforms)],
) -> PreviewRepresentationHandler:
    """Подключает все read adapters к одной сессии внешнего tenant UoW."""
    catalog = CatalogBindingsFacade(
        SqlAlchemyCatalogItemQueryRepository(uow.session),
        PostgresCatalogMutationLock(uow.session),
    )
    return PreviewRepresentationHandler(
        channels=SqlAlchemyChannelQueryRepository(uow.session),
        representations=SqlAlchemyRepresentationQueryRepository(uow.session),
        platforms=platforms,
        builder=RepresentationBuilder(
            catalog=RepresentationCatalogGateway(catalog),
            publications=SqlAlchemyCatalogBindingQueryRepository(uow.session),
        ),
        clock=clock,
    )


PreviewRepresentationHandlerDep = Annotated[
    PreviewRepresentationHandler, Depends(get_preview_representation_handler)
]
