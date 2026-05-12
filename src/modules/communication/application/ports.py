from __future__ import annotations

from src.modules.communication.application.message.ports import (
    CommunicationRepositoryFactory,
    HttpClientProtocol,
    OutboundMessagePublisherProtocol,
    OutboundMessageQueryRepositoryProtocol,
    OutboundProcessingByIdRepositoryProtocol,
    OutboundProcessingRepositoryProtocol,
    ProcessingContext,
    ProviderHttpResponse,
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderProtocol,
    ProviderSenderRegistryProtocol,
    SendCommunicationRepositoryProtocol,
)
from src.modules.communication.application.provider.ports import (
    ProviderConnectionRepositoryProtocol,
    ProviderConnectorRepositoryProtocol,
)
from src.modules.communication.application.queue.ports import (
    OutboundQueueRepositoryProtocol,
)
from src.modules.communication.application.template.ports import (
    MessageTemplateRepositoryProtocol,
)
from src.modules.communication.application.webhook.ports import (
    ProviderWebhookRepositoryProtocol,
)

__all__ = [
    "CommunicationRepositoryFactory",
    "HttpClientProtocol",
    "MessageTemplateRepositoryProtocol",
    "OutboundMessagePublisherProtocol",
    "OutboundMessageQueryRepositoryProtocol",
    "OutboundProcessingByIdRepositoryProtocol",
    "OutboundProcessingRepositoryProtocol",
    "OutboundQueueRepositoryProtocol",
    "ProcessingContext",
    "ProviderConnectionRepositoryProtocol",
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
