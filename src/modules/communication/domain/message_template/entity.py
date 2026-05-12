from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.communication.domain.message_template.value_object import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class MessageTemplate:
    template_id: MessageTemplateIdVO
    tenant_id: EntityIdVO
    template_code: str
    name: str
    description: str | None
    provider_connector_id: ProviderConnectorIdVO
    provider_message_type_id: ProviderMessageTypeIdVO
    channel_code: str
    message_class: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class TemplateVersion:
    template_version_id: TemplateVersionIdVO
    template_id: MessageTemplateIdVO
    version_no: int
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


__all__ = [
    "MessageTemplate",
    "TemplateVersion",
]
