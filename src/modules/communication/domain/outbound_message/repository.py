from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message.entity import (
    CommunicationRequest,
    OutboundMessage,
)
from src.modules.communication.domain.outbound_message.value_object import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


class OutboundMessageRepositoryProtocol(Protocol):
    """Порт командного хранения outbound message aggregate."""

    async def get_existing_send_by_idempotency(
        self,
        *,
        tenant_id: EntityIdVO,
        idempotency_key: str,
    ) -> tuple[CommunicationRequest, OutboundMessage] | None:
        """Возвращает ранее созданный send по idempotency key."""
        ...

    async def create_send_request(
        self,
        *,
        tenant_id: EntityIdVO,
        communication_request_id: CommunicationRequestIdVO,
        outbound_message_id: OutboundMessageIdVO,
        initiator_type: str,
        initiator_ref_id: str,
        correlation_id: EntityIdVO,
        idempotency_key: str,
        message_class: str,
        channel_code: str,
        template_id: MessageTemplateIdVO,
        template_version_id: TemplateVersionIdVO,
        recipient_identifier_type: str,
        recipient_address: str,
        recipient_snapshot: dict[str, Any],
        variables: dict[str, Any],
        scheduled_at: datetime | None,
        priority: int,
        provider_connection_id: ProviderConnectionIdVO,
        now: datetime,
    ) -> tuple[CommunicationRequest, OutboundMessage]:
        """Создает communication request и queued outbound message."""
        ...


__all__ = ["OutboundMessageRepositoryProtocol"]
