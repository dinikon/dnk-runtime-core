from fastapi import APIRouter
from src.modules.universal_access.presentation.http.controllers.add_crm_item import (
    router as add_crm_item_router,
)
from src.modules.universal_access.presentation.http.controllers.delete_crm_item import (
    router as delete_crm_item_router,
)
from src.modules.universal_access.presentation.http.controllers.get_crm_item import (
    router as get_crm_item_router,
)
from src.modules.universal_access.presentation.http.controllers.list_crm_item import (
    router as list_crm_item_router,
)
from src.modules.universal_access.presentation.http.controllers.update_crm_item import (
    router as update_crm_item_router,
)

router = APIRouter()
router.include_router(get_crm_item_router)
router.include_router(add_crm_item_router)
router.include_router(update_crm_item_router)
router.include_router(delete_crm_item_router)
router.include_router(list_crm_item_router)
