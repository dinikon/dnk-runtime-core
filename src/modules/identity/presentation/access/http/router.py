from fastapi import APIRouter
from src.modules.identity.presentation.access.http.controller.update_access import (
    router as update_access_router,
)
from src.modules.identity.presentation.access.http.controller.users import (
    router as users_router,
)

router = APIRouter()
router.include_router(users_router)
router.include_router(update_access_router)
