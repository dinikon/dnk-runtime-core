from fastapi import APIRouter, Depends
from src.modules.catalog.presentation.depends.transaction import (
    prepare_catalog_transaction,
)
from src.modules.catalog.presentation.catalog_item.router import router as items_router
from src.modules.catalog.presentation.product_type.router import router as schema_router
from src.modules.catalog.presentation.attribute.router import (
    router as attributes_router,
)
from src.modules.catalog.presentation.category.router import router as categories_router
from src.modules.catalog.presentation.tag.router import router as tags_router

router = APIRouter(dependencies=[Depends(prepare_catalog_transaction)])
router.include_router(items_router)
router.include_router(schema_router)
router.include_router(attributes_router)
router.include_router(categories_router)
router.include_router(tags_router)
