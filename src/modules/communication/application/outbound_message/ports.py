from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.communication.domain.delivery import (
    DeliveryAttempt,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateEntity,
    TemplateVersionEntity,
)
from src.modules.communication.domain.outbound_message import (
    CommunicationRequest,
    OutboundMessage,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnection,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderMessageType,
)


@dataclass(frozen=True, slots=True)
class ProviderHttpResponse:
    """Provider HTTP response snapshot."""

    status_code: int
    payload: Any


@dataclass(frozen=True, slots=True)
class ProviderSendContext:
    """Provider send context assembled from outbound state and connector config."""

    outbound_message_id: UUID
    communication_request_id: UUID
    initiator_ref_id: str | None
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    variables: dict[str, Any]
    connection_code: str
    channel_code: str
    provider_message_type_code: str
    config: dict[str, Any]
    secrets_b64: str | None
    connector_spec: dict[str, Any]
    send_spec: dict[str, Any]
    rendered_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProviderPreparedSend:
    """Prepared provider send with persisted-safe request snapshot."""

    request_payload: dict[str, Any]
    transport_payload: Any


@dataclass(frozen=True, slots=True)
class ProviderSendResult:
    """Normalized provider send result."""

    success: bool
    response_payload: dict[str, Any]
    http_status_code: int | None
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    error_code: str | None = None
    error_message: str | None = None


class HttpClientProtocol(Protocol):
    """Port for provider HTTP calls."""

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        json_body: Any,
        basic_auth: tuple[str, str] | None = None,
    ) -> ProviderHttpResponse:
        """Execute an HTTP request and return a response snapshot."""
        ...


class ProviderSenderProtocol(Protocol):
    """Port for provider-specific send transports."""

    transport: str

    def build(self, context: ProviderSendContext) -> ProviderPreparedSend:
        """Build a provider send request and redacted request snapshot."""
        ...

    async def send(
        self,
        context: ProviderSendContext,
        prepared: ProviderPreparedSend,
    ) -> ProviderSendResult:
        """Send a prepared provider request and return normalized result."""
        ...


class ProviderSenderRegistryProtocol(Protocol):
    """Port resolving provider senders by transport name."""

    def get(self, transport: str) -> ProviderSenderProtocol:
        """Return provider sender for transport."""
        ...


class OutboundMessagePublisherProtocol(Protocol):
    """Port for publishing outbound-message work to a broker."""

    async def publish(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        source: str,
        published_at: datetime,
    ) -> None:
        """Publish a communication outbound message job."""
        ...


ProcessingContext = tuple[
    OutboundMessage,
    CommunicationRequest,
    MessageTemplateEntity,
    TemplateVersionEntity,
    ProviderConnection,
    ProviderConnector,
    ProviderMessageType,
]


class SendCommunicationRepositoryProtocol(Protocol):
    async def get_existing_send_by_idempotency(
        self,
        *,
        tenant_id: UUID,
        idempotency_key: str,
    ) -> tuple[CommunicationRequest, OutboundMessage] | None: ...

    async def get_template(
        self,
        *,
        tenant_id: UUID,
        template_id: UUID,
    ) -> MessageTemplateEntity | None: ...

    async def get_template_by_code(
        self,
        *,
        tenant_id: UUID,
        template_code: str,
    ) -> MessageTemplateEntity | None: ...

    async def get_active_template_version(
        self,
        tenant_id: UUID,
        template_id: UUID,
    ) -> TemplateVersionEntity | None: ...

    async def find_active_connection(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        channel_code: str,
    ) -> ProviderConnection | None: ...

    async def create_send_request(
        self,
        *,
        tenant_id: UUID,
        initiator_type: str,
        initiator_ref_id: str | None,
        correlation_id: UUID | None,
        idempotency_key: str | None,
        message_class: str,
        channel_code: str,
        template_id: UUID,
        template_version_id: UUID,
        contact_id: UUID | None,
        recipient_address: str,
        recipient_snapshot: dict[str, Any],
        variables: dict[str, Any],
        scheduled_at: datetime | None,
        priority: int,
        provider_connection_id: UUID,
        now: datetime,
    ) -> tuple[CommunicationRequest, OutboundMessage]: ...


class OutboundProcessingRepositoryProtocol(Protocol):
    async def claim_queued_messages(
        self,
        tenant_id: UUID,
        limit: int,
    ) -> list[OutboundMessage]: ...

    async def load_processing_context(
        self,
        tenant_id: UUID,
        outbound_message_id: UUID,
    ) -> ProcessingContext: ...

    async def create_delivery_attempt(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        provider_connection_id: UUID,
        request_payload: dict[str, Any],
    ) -> DeliveryAttempt: ...

    async def complete_outbound_processing(self, **kwargs: Any) -> bool: ...

    async def fail_outbound_processing(self, **kwargs: Any) -> bool: ...


class OutboundProcessingByIdRepositoryProtocol(
    OutboundProcessingRepositoryProtocol, Protocol
):
    async def claim_outbound_for_processing(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        now: datetime,
        lease_until: datetime,
    ) -> OutboundMessage | None: ...

    async def get_outbound_by_id(
        self,
        tenant_id: UUID,
        outbound_message_id: UUID,
    ) -> OutboundMessage | None: ...


class OutboundMessageQueryRepositoryProtocol(Protocol):
    async def get_outbound(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
    ) -> OutboundMessage | None: ...

    async def list_outbound(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        offset: int,
    ) -> list[OutboundMessage]: ...


CommunicationRepositoryFactory = Callable[
    [AsyncSession],
    OutboundProcessingByIdRepositoryProtocol,
]


__all__ = [
    "CommunicationRepositoryFactory",
    "HttpClientProtocol",
    "OutboundMessagePublisherProtocol",
    "OutboundMessageQueryRepositoryProtocol",
    "OutboundProcessingByIdRepositoryProtocol",
    "OutboundProcessingRepositoryProtocol",
    "ProcessingContext",
    "ProviderHttpResponse",
    "ProviderPreparedSend",
    "ProviderSendContext",
    "ProviderSendResult",
    "ProviderSenderProtocol",
    "ProviderSenderRegistryProtocol",
    "SendCommunicationRepositoryProtocol",
]
