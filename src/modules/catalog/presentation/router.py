from fastapi import APIRouter
from src.modules.catalog.presentation.product.router import router as products_router
from src.modules.catalog.presentation.product_type.router import router as types_router
from src.modules.catalog.presentation.content_block.router import (
    router as blocks_router,
)

router = APIRouter()
router.include_router(products_router)
router.include_router(types_router)
router.include_router(blocks_router)
