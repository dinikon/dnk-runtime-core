from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.communication.application.outbound_message.processing import (
    OutboundProcessingByIdRepositoryProtocol,
    OutboundProcessingRepositoryContextFactoryProtocol,
    OutboundProcessingRepositoryProtocol,
    ProcessingContext,
)
from src.modules.communication.application.outbound_message.provider_send import (
    HttpClientProtocol,
    ProviderHttpResponse,
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderProtocol,
    ProviderSenderRegistryProtocol,
)
from src.modules.communication.application.outbound_message.query import (
    OutboundMessageQueryRepositoryProtocol,
)
from src.modules.communication.application.outbound_message.use_case import (
    ProviderConnectionLookupProtocol,
    SendCommunicationTemplateLookupProtocol,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageRepositoryProtocol,
)


class OutboundMessagePublisherProtocol(Protocol):
    """Port публикации outbound-message work в broker."""

    async def publish(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        source: str,
        published_at: datetime,
    ) -> None:
        """Публикует communication outbound message job."""
        ...


SendCommunicationRepositoryProtocol = OutboundMessageRepositoryProtocol
CommunicationRepositoryFactory = OutboundProcessingRepositoryContextFactoryProtocol


__all__ = [
    "CommunicationRepositoryFactory",
    "HttpClientProtocol",
    "OutboundMessagePublisherProtocol",
    "OutboundMessageQueryRepositoryProtocol",
    "OutboundMessageRepositoryProtocol",
    "OutboundProcessingByIdRepositoryProtocol",
    "OutboundProcessingRepositoryContextFactoryProtocol",
    "OutboundProcessingRepositoryProtocol",
    "ProcessingContext",
    "ProviderConnectionLookupProtocol",
    "ProviderHttpResponse",
    "ProviderPreparedSend",
    "ProviderSendContext",
    "ProviderSendResult",
    "ProviderSenderProtocol",
    "ProviderSenderRegistryProtocol",
    "SendCommunicationRepositoryProtocol",
    "SendCommunicationTemplateLookupProtocol",
]
