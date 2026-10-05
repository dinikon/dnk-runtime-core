from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.attribute.http.controller.create_attribute import (
    create_attribute,
)
from src.modules.catalog.presentation.attribute.http.controller.get_attribute import (
    get_attribute,
)
from src.modules.catalog.presentation.attribute.http.controller.list_attributes import (
    list_attributes,
)
from src.modules.catalog.presentation.attribute.http.response.create_attribute import (
    CreateAttributeResponse,
)
from src.modules.catalog.presentation.attribute.http.response.get_attribute import (
    GetAttributeResponse,
)
from src.modules.catalog.presentation.attribute.http.response.list_attributes import (
    ListAttributesResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/attributes", tags=["catalog-attributes"])
router.add_api_route(
    "",
    create_attribute,
    methods=["POST"],
    status_code=201,
    response_model=CreateAttributeResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_attributes,
    methods=["GET"],
    response_model=ListAttributesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{attribute_id}",
    get_attribute,
    methods=["GET"],
    response_model=GetAttributeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
