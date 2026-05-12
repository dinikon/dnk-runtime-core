from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


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


__all__ = [
    "HttpClientProtocol",
    "OutboundMessagePublisherProtocol",
    "ProviderHttpResponse",
    "ProviderPreparedSend",
    "ProviderSendContext",
    "ProviderSendResult",
    "ProviderSenderProtocol",
    "ProviderSenderRegistryProtocol",
]
