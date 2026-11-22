from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.catalog.presentation.catalog_category.http.response.create_catalog_category import (
    CreateCatalogCategoryResponse,
)
from src.modules.catalog.presentation.catalog_category.http.controller.create_catalog_category import (
    create_catalog_category,
)
from src.modules.catalog.presentation.catalog_category.http.response.update_catalog_category import (
    UpdateCatalogCategoryResponse,
)
from src.modules.catalog.presentation.catalog_category.http.controller.update_catalog_category import (
    update_catalog_category,
)
from src.modules.catalog.presentation.catalog_category.http.controller.delete_catalog_category import (
    delete_catalog_category,
)
from src.modules.catalog.presentation.catalog_category.http.response.set_default_catalog_category import (
    SetDefaultCatalogCategoryResponse,
)
from src.modules.catalog.presentation.catalog_category.http.controller.set_default_catalog_category import (
    set_default_catalog_category,
)
from src.modules.catalog.presentation.catalog_category.http.response.list_catalog_categories import (
    ListCatalogCategoriesResponse,
)
from src.modules.catalog.presentation.catalog_category.http.controller.list_catalog_categories import (
    list_catalog_categories,
)

router = APIRouter(prefix="/catalog/categories", tags=["catalog-category"])
router.add_api_route(
    "",
    create_catalog_category,
    methods=["POST"],
    status_code=201,
    response_model=CreateCatalogCategoryResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{category_id}",
    update_catalog_category,
    methods=["PATCH"],
    status_code=200,
    response_model=UpdateCatalogCategoryResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{category_id}",
    delete_catalog_category,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/default",
    set_default_catalog_category,
    methods=["PUT"],
    status_code=200,
    response_model=SetDefaultCatalogCategoryResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "",
    list_catalog_categories,
    methods=["GET"],
    status_code=200,
    response_model=ListCatalogCategoriesResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
