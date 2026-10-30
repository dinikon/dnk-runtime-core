from fastapi import APIRouter, Depends

from src.modules.channels.presentation.stock_sync.http.route import StockRoute
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.channels.presentation.stock_sync.http.controller.get_binding_stock import (
    get_binding_stock,
)
from src.modules.channels.presentation.stock_sync.http.response.get_binding_stock import (
    GetBindingStockResponse,
)
from src.modules.channels.presentation.stock_sync.http.controller.refresh_publication_stock import (
    refresh_publication_stock,
)
from src.modules.channels.presentation.stock_sync.http.response.refresh_publication_stock import (
    RefreshPublicationStockResponse,
)
from src.modules.channels.presentation.stock_sync.http.controller.export_catalog_stock import (
    export_catalog_stock,
)
from src.modules.channels.presentation.stock_sync.http.response.export_catalog_stock import (
    ExportCatalogStockResponse,
)

router = APIRouter(prefix="/channels", tags=["channel-stock"], route_class=StockRoute)

router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/stock",
    get_binding_stock,
    methods=["GET"],
    response_model=GetBindingStockResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/stock-import",
    refresh_publication_stock,
    methods=["POST"],
    status_code=202,
    response_model=RefreshPublicationStockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{channel_id}/catalog-bindings/{group_id}/stock-export",
    export_catalog_stock,
    methods=["POST"],
    status_code=202,
    response_model=ExportCatalogStockResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
