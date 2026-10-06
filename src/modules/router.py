from fastapi import APIRouter

from src.modules.inventory.presentation.sku.router import router as skus_router
from src.modules.catalog.presentation.product.router import router as products_router
from src.modules.catalog.presentation.category.router import router as categories_router
from src.modules.catalog.presentation.content_block.router import (
    router as catalog_blocks_router,
)
from src.modules.catalog.presentation.product_type.router import (
    router as catalog_types_router,
)
from src.modules.crm.presentation.contact.router import router as contacts_router
from src.modules.crm.presentation.company.router import router as companies_router
from src.modules.contact_points.presentation.router import (
    router as contact_points_router,
)
from src.modules.identity.presentation.auth.http.router import router as identity_router
from src.modules.price_lists.presentation.http.router import (
    offers_router as price_list_offers_router,
)
from src.modules.price_lists.presentation.http.router import (
    router as price_lists_router,
)

from src.modules.tenancy.presentation.http.router import router as tenancy_router
from src.modules.reference_data.presentation.router import (
    router as reference_data_router,
)

router = APIRouter(prefix="/api/console")

router.include_router(tenancy_router)
router.include_router(reference_data_router)
router.include_router(skus_router)
router.include_router(products_router)
router.include_router(categories_router)
router.include_router(catalog_blocks_router)
router.include_router(catalog_types_router)
router.include_router(identity_router)
router.include_router(contact_points_router)
router.include_router(contacts_router)
router.include_router(companies_router)
router.include_router(price_lists_router)
router.include_router(price_list_offers_router)

__all__ = ["router"]
