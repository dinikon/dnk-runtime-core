from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.catalog.presentation.tag.http.controller.create_tag import (
    create_tag,
)
from src.modules.catalog.presentation.tag.http.response.create_tag import (
    CreateTagResponse,
)
from src.modules.catalog.presentation.tag.http.controller.put_tag_translation import (
    put_tag_translation,
)
from src.modules.catalog.presentation.tag.http.response.put_tag_translation import (
    PutTagTranslationResponse,
)
from src.modules.catalog.presentation.tag.http.controller.delete_tag import (
    delete_tag,
)
from src.modules.catalog.presentation.tag.http.controller.get_tag import (
    get_tag,
)
from src.modules.catalog.presentation.tag.http.response.get_tag import (
    GetTagResponse,
)
from src.modules.catalog.presentation.tag.http.controller.list_tags import (
    list_tags,
)
from src.modules.catalog.presentation.tag.http.response.list_tags import (
    ListTagsResponse,
)

router = APIRouter(prefix="/catalog/tags", tags=["catalog-tag"])
router.add_api_route(
    "",
    create_tag,
    methods=["POST"],
    status_code=201,
    response_model=CreateTagResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{tag_id}/translations/{locale}",
    put_tag_translation,
    methods=["PUT"],
    status_code=200,
    response_model=PutTagTranslationResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{tag_id}",
    delete_tag,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{tag_id}",
    get_tag,
    methods=["GET"],
    status_code=200,
    response_model=GetTagResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    list_tags,
    methods=["GET"],
    status_code=200,
    response_model=ListTagsResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
