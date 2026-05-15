from __future__ import annotations

from fastapi import APIRouter

from src.modules.communication.presentation.http import (
    delivery,
    message_template,
    outbound_message,
    provider_connection,
    provider_connector,
)

router = APIRouter()
router.include_router(provider_connector.router)
router.include_router(provider_connection.router)
router.include_router(message_template.router)
router.include_router(outbound_message.router)
router.include_router(delivery.router)

__all__ = ["router"]
