from __future__ import annotations

from fastapi import APIRouter

from src.modules.communication.presentation.http.outbound_message.controller.get_message import (
    get_message,
    router as get_message_router,
)
from src.modules.communication.presentation.http.outbound_message.controller.list_messages import (
    list_messages,
    router as list_messages_router,
)
from src.modules.communication.presentation.http.outbound_message.controller.send_communication import (
    _publish_send_job_after_commit,
    router as send_communication_router,
    send_communication,
)
from src.modules.communication.presentation.http.outbound_message.requests import (
    SendCommunicationRequestSchema,
)
from src.modules.communication.presentation.http.outbound_message.responses import (
    ListOutboundMessagesResponseSchema,
    OutboundMessageResponseSchema,
    SendCommunicationResponseSchema,
)

router = APIRouter()
router.include_router(send_communication_router)
router.include_router(list_messages_router)
router.include_router(get_message_router)

__all__ = [
    "ListOutboundMessagesResponseSchema",
    "OutboundMessageResponseSchema",
    "SendCommunicationRequestSchema",
    "SendCommunicationResponseSchema",
    "_publish_send_job_after_commit",
    "get_message",
    "list_messages",
    "router",
    "send_communication",
]
