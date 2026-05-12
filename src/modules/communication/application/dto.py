from __future__ import annotations

from src.modules.communication.application.message.dto import (
    OutboundMessageDTO,
    ProcessOutboundMessageResultDTO,
    ProcessQueuedResultDTO,
    SendCommunicationResultDTO,
)
from src.modules.communication.application.provider.dto import (
    ProviderConnectionDTO,
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
)
from src.modules.communication.application.queue.dto import (
    OutboundMessageJob,
    PublishQueuedResultDTO,
    RecoverStuckResultDTO,
)
from src.modules.communication.application.template.dto import (
    MessageTemplateDTO,
    TemplateVersionDTO,
)
from src.modules.communication.application.webhook.dto import WebhookResultDTO

__all__ = [
    "MessageTemplateDTO",
    "OutboundMessageDTO",
    "OutboundMessageJob",
    "ProcessOutboundMessageResultDTO",
    "ProcessQueuedResultDTO",
    "ProviderConnectionDTO",
    "ProviderConnectorDTO",
    "ProviderMessageTypeDTO",
    "PublishQueuedResultDTO",
    "RecoverStuckResultDTO",
    "SendCommunicationResultDTO",
    "TemplateVersionDTO",
    "WebhookResultDTO",
]
