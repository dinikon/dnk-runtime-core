from fastapi import APIRouter, Depends, Response
from src.modules.inventory.presentation.inventory_item.http.controller.get_inventory_item import (
    get_inventory_item,
)
from src.modules.inventory.presentation.inventory_item.http.response.get_inventory_item import (
    GetInventoryItemResponse,
)
from src.modules.inventory.presentation.inventory_item.http.controller.put_inventory_item import (
    put_inventory_item,
)
from src.modules.inventory.presentation.inventory_item.http.controller.patch_inventory_item import (
    patch_inventory_item,
)
from src.modules.inventory.presentation.inventory_item.http.controller.delete_inventory_item import (
    delete_inventory_item,
)
from src.modules.inventory.presentation.inventory_item.http.response.put_inventory_item import (
    PutInventoryItemResponse,
)
from src.modules.inventory.presentation.inventory_item.http.response.patch_inventory_item import (
    PatchInventoryItemResponse,
)

from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.inventory_item.http.controller.create_inventory_item import (
    create_inventory_item,
)
from src.modules.inventory.presentation.inventory_item.http.controller.list_inventory_items import (
    list_inventory_items,
)
from src.modules.inventory.presentation.inventory_item.http.response.create_inventory_item import (
    CreateInventoryItemResponse,
)
from src.modules.inventory.presentation.inventory_item.http.response.list_inventory_items import (
    ListInventoryItemsResponse,
)

router = APIRouter(prefix="/inventory/items", tags=["inventory-items"])
router.add_api_route(
    "/{inventory_item_id}",
    get_inventory_item,
    methods=["GET"],
    response_model=GetInventoryItemResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_inventory_item,
    methods=["POST"],
    status_code=201,
    response_model=CreateInventoryItemResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_inventory_items,
    methods=["GET"],
    response_model=ListInventoryItemsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{inventory_item_id}",
    put_inventory_item,
    methods=["PUT"],
    response_model=PutInventoryItemResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{inventory_item_id}",
    patch_inventory_item,
    methods=["PATCH"],
    response_model=PatchInventoryItemResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{inventory_item_id}",
    delete_inventory_item,
    methods=["DELETE"],
    status_code=204,
    response_class=Response,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
