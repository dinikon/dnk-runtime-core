from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.depends import tenant_id_from_context
from src.modules.channels.presentation.stock_sync.assembly import (
    StockRuntime,
    build_stock_runtime,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.application.stock_sync.command.refresh_publication_stock.handler import (
    RefreshPublicationStockHandler,
)
from src.modules.channels.application.stock_sync.command.export_catalog_stock.handler import (
    ExportCatalogStockHandler,
)
from src.modules.channels.application.stock_sync.query.get_binding_stock.handler import (
    GetBindingStockHandler,
)


def get_stock_runtime(
    uow: UoWDep, context: AuthenticatedRequestContextDep
) -> StockRuntime:
    """Собирает порты на общем request UoW."""
    return build_stock_runtime(uow.session, tenant_id_from_context(context))


StockRuntimeDep = Annotated[StockRuntime, Depends(get_stock_runtime)]


def get_refresh_publication_stock_handler(
    runtime: StockRuntimeDep, clock: ClockDep
) -> RefreshPublicationStockHandler:
    """Собирает сценарий получения наблюдаемого остатка."""
    return RefreshPublicationStockHandler(runtime.operations, clock)


RefreshPublicationStockHandlerDep = Annotated[
    RefreshPublicationStockHandler, Depends(get_refresh_publication_stock_handler)
]


def get_export_catalog_stock_handler(
    runtime: StockRuntimeDep, clock: ClockDep
) -> ExportCatalogStockHandler:
    """Собирает сценарий отправки количества Catalog."""
    return ExportCatalogStockHandler(runtime.operations, clock)


ExportCatalogStockHandlerDep = Annotated[
    ExportCatalogStockHandler, Depends(get_export_catalog_stock_handler)
]


def get_get_binding_stock_handler(
    runtime: StockRuntimeDep, uow: UoWDep, clock: ClockDep
) -> GetBindingStockHandler:
    """Использует SQL read проекции без Aggregate для отображения."""
    return GetBindingStockHandler(
        channels=SqlAlchemyChannelQueryRepository(uow.session),
        planning=runtime.planning,
        read=runtime.read,
        clock=clock,
    )


GetBindingStockHandlerDep = Annotated[
    GetBindingStockHandler, Depends(get_get_binding_stock_handler)
]
