from fastapi import APIRouter, Depends

from src.modules.catalog.presentation.category.http.controller.create_category import (
    create_category,
)
from src.modules.catalog.presentation.category.http.controller.delete_category import (
    delete_category,
)
from src.modules.catalog.presentation.category.http.controller.get_category import (
    get_category,
)
from src.modules.catalog.presentation.category.http.controller.list_categories import (
    list_categories,
)
from src.modules.catalog.presentation.category.http.controller.move_category import (
    move_category,
)
from src.modules.catalog.presentation.category.http.controller.put_category_content import (
    put_category_content,
)
from src.modules.catalog.presentation.category.http.response.create_category import (
    CreateCategoryResponse,
)
from src.modules.catalog.presentation.category.http.response.get_category import (
    GetCategoryResponse,
)
from src.modules.catalog.presentation.category.http.response.list_categories import (
    ListCategoryResponse,
)
from src.modules.catalog.presentation.category.http.response.move_category import (
    MoveCategoryResponse,
)
from src.modules.catalog.presentation.category.http.response.put_category_content import (
    PutCategoryContentResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/catalog/categories", tags=["catalog-categories"])
router.add_api_route(
    "",
    create_category,
    methods=["POST"],
    status_code=201,
    response_model=CreateCategoryResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_categories,
    methods=["GET"],
    response_model=list[ListCategoryResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{category_id}",
    get_category,
    methods=["GET"],
    response_model=GetCategoryResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{category_id}/contents/{locale}",
    put_category_content,
    methods=["PUT"],
    response_model=PutCategoryContentResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{category_id}/parent",
    move_category,
    methods=["PUT"],
    response_model=MoveCategoryResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{category_id}",
    delete_category,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
