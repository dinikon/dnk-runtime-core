from fastapi import APIRouter

from src.modules.identity.presentation.api.console_auth import (
    router as console_auth_router,
)

router = APIRouter()
router.include_router(console_auth_router)

__all__ = ["router"]
