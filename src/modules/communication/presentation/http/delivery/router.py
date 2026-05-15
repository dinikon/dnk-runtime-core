from fastapi import APIRouter

from src.modules.communication.presentation.http.delivery.controller import (
    handle_provider_webhook,
)

router = APIRouter()
router.include_router(handle_provider_webhook.router)

__all__ = ["router"]
