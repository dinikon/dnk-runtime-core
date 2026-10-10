from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.catalog.presentation.attribute.http.controller.create_attribute import (
    create_attribute,
)
from src.modules.catalog.presentation.attribute.http.response.create_attribute import (
    CreateAttributeResponse,
)
from src.modules.catalog.presentation.attribute.http.controller.put_attribute_translation import (
    put_attribute_translation,
)
from src.modules.catalog.presentation.attribute.http.response.put_attribute_translation import (
    PutAttributeTranslationResponse,
)
from src.modules.catalog.presentation.attribute.http.controller.replace_attribute_options import (
    replace_attribute_options,
)
from src.modules.catalog.presentation.attribute.http.response.replace_attribute_options import (
    ReplaceAttributeOptionsResponse,
)
from src.modules.catalog.presentation.attribute.http.controller.delete_attribute import (
    delete_attribute,
)
from src.modules.catalog.presentation.attribute.http.controller.get_attribute import (
    get_attribute,
)
from src.modules.catalog.presentation.attribute.http.response.get_attribute import (
    GetAttributeResponse,
)
from src.modules.catalog.presentation.attribute.http.controller.list_attributes import (
    list_attributes,
)
from src.modules.catalog.presentation.attribute.http.response.list_attributes import (
    ListAttributesResponse,
)

router = APIRouter(prefix="/catalog/attributes", tags=["catalog-attribute"])
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
    "/{attribute_id}/translations/{locale}",
    put_attribute_translation,
    methods=["PUT"],
    status_code=200,
    response_model=PutAttributeTranslationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{attribute_id}/options/{locale}",
    replace_attribute_options,
    methods=["PUT"],
    status_code=200,
    response_model=ReplaceAttributeOptionsResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{attribute_id}",
    delete_attribute,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{attribute_id}",
    get_attribute,
    methods=["GET"],
    status_code=200,
    response_model=GetAttributeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_attributes,
    methods=["GET"],
    status_code=200,
    response_model=ListAttributesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
