from dataclasses import dataclass

from src.modules.communication.domain.message_template import MessageTemplateIdVO
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateMessageTemplateCommand:
    """Команда application-слоя на создание message template."""

    tenant_id: EntityIdVO
    template_id: MessageTemplateIdVO
    name: str
    description: str | None
    provider_connector_id: ProviderConnectorIdVO
    provider_message_type_id: ProviderMessageTypeIdVO
    channel_code: str


__all__ = ["CreateMessageTemplateCommand"]
