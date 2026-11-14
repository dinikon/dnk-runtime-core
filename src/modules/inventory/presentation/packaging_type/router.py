from fastapi import APIRouter, Depends, Response

from src.modules.inventory.presentation.packaging_type.http.controller.put_packaging_type import (
    put_packaging_type,
)
from src.modules.inventory.presentation.packaging_type.http.controller.patch_packaging_type import (
    patch_packaging_type,
)
from src.modules.inventory.presentation.packaging_type.http.response.put_packaging_type import (
    PutPackagingTypeResponse,
)
from src.modules.inventory.presentation.packaging_type.http.response.patch_packaging_type import (
    PatchPackagingTypeResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.inventory.presentation.packaging_type.http.controller.create_packaging_type import (
    create_packaging_type,
)
from src.modules.inventory.presentation.packaging_type.http.controller.delete_packaging_type import (
    delete_packaging_type,
)
from src.modules.inventory.presentation.packaging_type.http.controller.get_packaging_type import (
    get_packaging_type,
)
from src.modules.inventory.presentation.packaging_type.http.controller.list_packaging_types import (
    list_packaging_types,
)
from src.modules.inventory.presentation.packaging_type.http.response.create_packaging_type import (
    CreatePackagingTypeResponse,
)
from src.modules.inventory.presentation.packaging_type.http.response.get_packaging_type import (
    GetPackagingTypeResponse,
)
from src.modules.inventory.presentation.packaging_type.http.response.list_packaging_types import (
    ListPackagingTypesResponse,
)

router = APIRouter(
    prefix="/inventory/packaging-types", tags=["inventory-packaging-types"]
)
router.add_api_route(
    "/{packaging_type_id}",
    put_packaging_type,
    methods=["PUT"],
    response_model=PutPackagingTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{packaging_type_id}",
    patch_packaging_type,
    methods=["PATCH"],
    response_model=PatchPackagingTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    create_packaging_type,
    methods=["POST"],
    status_code=201,
    response_model=CreatePackagingTypeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_packaging_types,
    methods=["GET"],
    response_model=ListPackagingTypesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{packaging_type_id}",
    get_packaging_type,
    methods=["GET"],
    response_model=GetPackagingTypeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)

router.add_api_route(
    "/{packaging_type_id}",
    delete_packaging_type,
    methods=["DELETE"],
    status_code=204,
    response_class=Response,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
