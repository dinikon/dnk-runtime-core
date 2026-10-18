from fastapi import APIRouter, Depends
from src.modules.catalog.presentation.depends.transaction import (
    prepare_catalog_transaction,
)
from src.modules.catalog.presentation.catalog_item.router import router as items_router
from src.modules.catalog.presentation.product_type.router import router as schema_router

router = APIRouter(dependencies=[Depends(prepare_catalog_transaction)])
router.include_router(items_router)
router.include_router(schema_router)
