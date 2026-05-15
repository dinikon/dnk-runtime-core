from __future__ import annotations

from fastapi import APIRouter

from src.modules.communication.presentation.http.outbound_message.controller import (
    get_message,
    list_messages,
    send_communication,
)

router = APIRouter()
router.include_router(send_communication.router)
router.include_router(list_messages.router)
router.include_router(get_message.router)

__all__ = ["router"]
