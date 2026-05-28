from fastapi import APIRouter

from src.modules.communication.presentation.http.delivery.controller import (
    handle_provider_webhook,
    list_delivery_attempts,
    list_delivery_events,
    list_message_delivery_attempts,
    list_message_delivery_events,
)

router = APIRouter()
router.include_router(handle_provider_webhook.router)
router.include_router(list_message_delivery_attempts.router)
router.include_router(list_delivery_attempts.router)
router.include_router(list_message_delivery_events.router)
router.include_router(list_delivery_events.router)

__all__ = ["router"]
