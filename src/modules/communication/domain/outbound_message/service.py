from __future__ import annotations

from datetime import datetime
from typing import Any

from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message.entity import (
    CommunicationRequest,
    OutboundMessage,
)
from src.modules.communication.domain.outbound_message.repository import (
    OutboundMessageRepositoryProtocol,
)
from src.modules.communication.domain.outbound_message.value_object import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection import ProviderConnectionIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class OutboundMessageService:
    """Доменный сервис создания communication request и outbound message."""

    def __init__(
        self,
        *,
        repository: OutboundMessageRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис repository и clock-портом."""
        self._repository = repository
        self._clock = clock

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
    ) -> tuple[CommunicationRequest, OutboundMessage]:
        """Создает send request через repository, нормализуя входные значения."""
        now = self._clock.now()
        request = CommunicationRequest.create(
            communication_request_id=communication_request_id,
            tenant_id=tenant_id,
            initiator_type=initiator_type,
            initiator_ref_id=initiator_ref_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            channel_code=channel_code,
            template_id=template_id,
            template_version_id=template_version_id,
            recipient_identifier_type=recipient_identifier_type,
            recipient_address=recipient_address,
            recipient_snapshot=recipient_snapshot,
            variables=variables,
            scheduled_at=scheduled_at,
            priority=priority,
            now=now,
        )
        outbound = OutboundMessage.create_queued(
            outbound_message_id=outbound_message_id,
            tenant_id=tenant_id,
            communication_request_id=communication_request_id,
            provider_connection_id=provider_connection_id,
            channel_code=channel_code,
            priority=priority,
            recipient_identifier_type=recipient_identifier_type,
            recipient_address=recipient_address,
            recipient_snapshot=recipient_snapshot,
            now=now,
        )
        return await self._repository.create_send_request(
            tenant_id=tenant_id,
            communication_request_id=communication_request_id,
            outbound_message_id=outbound_message_id,
            initiator_type=request.initiator_type,
            initiator_ref_id=request.initiator_ref_id,
            correlation_id=request.correlation_id,
            idempotency_key=request.idempotency_key,
            channel_code=request.channel_code,
            template_id=request.template_id,
            template_version_id=request.template_version_id,
            recipient_identifier_type=request.recipient_identifier_type,
            recipient_address=request.recipient_address,
            recipient_snapshot=request.recipient_snapshot,
            variables=request.variables,
            scheduled_at=request.scheduled_at,
            priority=outbound.priority,
            provider_connection_id=provider_connection_id,
            now=now,
        )


__all__ = ["OutboundMessageService"]
