from fastapi import APIRouter
from src.modules.identity.presentation.user.http.controller.get_current_user import (
    router as get_router,
)
from src.modules.identity.presentation.user.http.controller.update_current_user_profile import (
    router as update_router,
)

router = APIRouter()
router.include_router(get_router)
router.include_router(update_router)
