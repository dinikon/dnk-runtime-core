from fastapi import APIRouter

from src.modules.inventory.presentation.http.category.controller import (
    create_category_router,
    delete_category_router,
    describe_category_fields_router,
    get_category_router,
    list_categories_router,
    update_category_router,
)
from src.modules.inventory.presentation.http.product.controller import (
    create_product_router,
    delete_product_router,
    describe_product_fields_router,
    get_product_router,
    list_products_router,
    update_product_router,
)

router = APIRouter()
router.include_router(create_product_router)
router.include_router(list_products_router)
router.include_router(describe_product_fields_router)
router.include_router(get_product_router)
router.include_router(update_product_router)
router.include_router(delete_product_router)
router.include_router(create_category_router)
router.include_router(list_categories_router)
router.include_router(describe_category_fields_router)
router.include_router(get_category_router)
router.include_router(update_category_router)
router.include_router(delete_category_router)

__all__ = ["router"]
