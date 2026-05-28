from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.message_template.value_object import (
    ChannelCodeVO,
    MessageClassVO,
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message.enum import (
    OutboundMessageStatus,
    RequestStatus,
)
from src.modules.communication.domain.outbound_message.value_object import (
    CommunicationRequestIdVO,
    IdempotencyKeyVO,
    InitiatorTypeVO,
    OutboundMessageIdVO,
    OutboundPriorityVO,
    RecipientAddressVO,
    RecipientIdentifierTypeVO,
)
from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class CommunicationRequest:
    """Доменная сущность communication request."""

    communication_request_id: CommunicationRequestIdVO
    tenant_id: EntityIdVO
    initiator_type: str
    initiator_ref_id: str
    correlation_id: EntityIdVO
    idempotency_key: str
    message_class: str
    channel_code: str
    template_id: MessageTemplateIdVO
    template_version_id: TemplateVersionIdVO
    recipient_identifier_type: str
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    variables: dict[str, Any]
    scheduled_at: datetime | None
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        communication_request_id: CommunicationRequestIdVO,
        tenant_id: EntityIdVO,
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
        now: datetime,
        status: str = RequestStatus.QUEUED.value,
    ) -> Self:
        """Создает communication request с нормализованными значениями."""
        return cls(
            communication_request_id=communication_request_id,
            tenant_id=tenant_id,
            initiator_type=InitiatorTypeVO(initiator_type).value,
            initiator_ref_id=_required_text(initiator_ref_id),
            correlation_id=correlation_id,
            idempotency_key=IdempotencyKeyVO(idempotency_key).value,
            message_class=MessageClassVO(message_class).value,
            channel_code=ChannelCodeVO(channel_code).value,
            template_id=template_id,
            template_version_id=template_version_id,
            recipient_identifier_type=RecipientIdentifierTypeVO(
                recipient_identifier_type
            ).value,
            recipient_address=RecipientAddressVO(recipient_address).value,
            recipient_snapshot=dict(recipient_snapshot),
            variables=dict(variables),
            scheduled_at=scheduled_at,
            priority=OutboundPriorityVO(priority).value,
            status=RequestStatus(status).value,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class OutboundMessage:
    """Доменная сущность outbound provider message."""

    outbound_message_id: OutboundMessageIdVO
    tenant_id: EntityIdVO
    communication_request_id: CommunicationRequestIdVO
    provider_connection_id: ProviderConnectionIdVO
    channel_code: str
    message_class: str
    priority: int
    recipient_identifier_type: str
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    rendered_payload: dict[str, Any]
    provider_request_payload: dict[str, Any]
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    error_code: str | None
    error_message: str | None
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    processing_token: EntityIdVO | None
    processing_started_at: datetime | None
    processing_deadline_at: datetime | None
    next_attempt_at: datetime | None
    queue_published_at: datetime | None
    queue_publish_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_queued(
        cls,
        *,
        outbound_message_id: OutboundMessageIdVO,
        tenant_id: EntityIdVO,
        communication_request_id: CommunicationRequestIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        channel_code: str,
        message_class: str,
        priority: int,
        recipient_identifier_type: str,
        recipient_address: str,
        recipient_snapshot: dict[str, Any],
        now: datetime,
    ) -> Self:
        """Создает queued outbound message с пустыми provider payload snapshots."""
        return cls(
            outbound_message_id=outbound_message_id,
            tenant_id=tenant_id,
            communication_request_id=communication_request_id,
            provider_connection_id=provider_connection_id,
            channel_code=ChannelCodeVO(channel_code).value,
            message_class=MessageClassVO(message_class).value,
            priority=OutboundPriorityVO(priority).value,
            recipient_identifier_type=RecipientIdentifierTypeVO(
                recipient_identifier_type
            ).value,
            recipient_address=RecipientAddressVO(recipient_address).value,
            recipient_snapshot=dict(recipient_snapshot),
            rendered_payload={},
            provider_request_payload={},
            external_message_id=None,
            external_status=None,
            internal_status=OutboundMessageStatus.QUEUED.value,
            error_code=None,
            error_message=None,
            queued_at=now,
            sent_at=None,
            delivered_at=None,
            failed_at=None,
            processing_token=None,
            processing_started_at=None,
            processing_deadline_at=None,
            next_attempt_at=None,
            queue_published_at=None,
            queue_publish_count=0,
            created_at=now,
            updated_at=now,
        )

    def mark_published(self, published_at: datetime) -> None:
        """Фиксирует публикацию outbound message в очередь."""
        self.queue_published_at = published_at
        self.queue_publish_count = int(self.queue_publish_count or 0) + 1
        self.updated_at = published_at


__all__ = [
    "CommunicationRequest",
    "OutboundMessage",
]


def _required_text(value: str) -> str:
    if not isinstance(value, str):
        raise CommunicationValidationError("Communication text value must be a string.")
    normalized = value.strip()
    if not normalized:
        raise CommunicationValidationError(
            "Communication text value must not be blank."
        )
    return normalized
