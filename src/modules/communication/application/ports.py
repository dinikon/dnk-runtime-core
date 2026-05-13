from __future__ import annotations

from src.modules.communication.application.outbound_message.ports import (
    CommunicationRepositoryFactory,
    HttpClientProtocol,
    OutboundMessagePublisherProtocol,
    OutboundMessageQueryRepositoryProtocol,
    OutboundProcessingByIdRepositoryProtocol,
    OutboundProcessingRepositoryProtocol,
    ProcessingContext,
    ProviderConnectionLookupProtocol,
    ProviderHttpResponse,
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderProtocol,
    ProviderSenderRegistryProtocol,
    SendCommunicationRepositoryProtocol,
)
from src.modules.communication.application.provider_connection.query import (
    ProviderConnectionQueryRepositoryProtocol,
)
from src.modules.communication.application.provider_connector.ports import (
    ProviderConnectorRepositoryProtocol,
)
from src.modules.communication.application.outbound_message.queue.ports import (
    OutboundQueueRepositoryProtocol,
)
from src.modules.communication.application.message_template.query import (
    MessageTemplateQueryRepositoryProtocol,
)
from src.modules.communication.application.delivery.ports import (
    ProviderWebhookRepositoryProtocol,
)

__all__ = [
    "CommunicationRepositoryFactory",
    "HttpClientProtocol",
    "MessageTemplateQueryRepositoryProtocol",
    "OutboundMessagePublisherProtocol",
    "OutboundMessageQueryRepositoryProtocol",
    "OutboundProcessingByIdRepositoryProtocol",
    "OutboundProcessingRepositoryProtocol",
    "OutboundQueueRepositoryProtocol",
    "ProcessingContext",
    "ProviderConnectionQueryRepositoryProtocol",
    "ProviderConnectionLookupProtocol",
    "ProviderConnectorRepositoryProtocol",
    "ProviderHttpResponse",
    "ProviderPreparedSend",
    "ProviderSendContext",
    "ProviderSendResult",
    "ProviderSenderProtocol",
    "ProviderSenderRegistryProtocol",
    "ProviderWebhookRepositoryProtocol",
    "SendCommunicationRepositoryProtocol",
]
