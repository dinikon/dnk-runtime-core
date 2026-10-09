from fastapi import APIRouter, Depends

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.warehousing.presentation.warehouse.http.controller.create_warehouse import (
    create_warehouse,
)
from src.modules.warehousing.presentation.warehouse.http.controller.get_warehouse import (
    get_warehouse,
)
from src.modules.warehousing.presentation.warehouse.http.controller.list_warehouses import (
    list_warehouses,
)
from src.modules.warehousing.presentation.warehouse.http.response.create_warehouse import (
    CreateWarehouseResponse,
)
from src.modules.warehousing.presentation.warehouse.http.response.get_warehouse import (
    GetWarehouseResponse,
)
from src.modules.warehousing.presentation.warehouse.http.response.list_warehouses import (
    ListWarehousesResponse,
)

router = APIRouter(prefix="/warehouses", tags=["warehousing-warehouses"])
router.add_api_route(
    "",
    create_warehouse,
    methods=["POST"],
    status_code=201,
    response_model=CreateWarehouseResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_warehouses,
    methods=["GET"],
    response_model=ListWarehousesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{warehouse_id}",
    get_warehouse,
    methods=["GET"],
    response_model=GetWarehouseResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
