from fastapi import APIRouter

from src.modules.communication.presentation.http.delivery.controller import (
    handle_provider_webhook_router,
)

router = APIRouter()
router.include_router(handle_provider_webhook_router)

__all__ = ["router"]
