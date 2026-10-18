from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.catalog.presentation.product_type.http.controller.get_default_product_type import (
    get_default_product_type,
)
from src.modules.catalog.presentation.product_type.http.response.get_default_product_type import (
    GetDefaultProductTypeResponse,
)

router = APIRouter(prefix="/catalog/product-type", tags=["catalog-schema"])
router.add_api_route(
    "/default",
    get_default_product_type,
    methods=["GET"],
    response_model=GetDefaultProductTypeResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
