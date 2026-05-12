from __future__ import annotations

from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ProviderConnectorIdVO(EntityIdVO):
    """Communication provider connector id."""


@dataclass(frozen=True, slots=True)
class ProviderMessageTypeIdVO(EntityIdVO):
    """Communication provider message type id."""


@dataclass(frozen=True, slots=True)
class ProviderConnectionIdVO(EntityIdVO):
    """Communication provider connection id."""


@dataclass(frozen=True, slots=True)
class MessageTemplateIdVO(EntityIdVO):
    """Communication message template id."""


@dataclass(frozen=True, slots=True)
class TemplateVersionIdVO(EntityIdVO):
    """Communication template version id."""


@dataclass(frozen=True, slots=True)
class CommunicationRequestIdVO(EntityIdVO):
    """Communication request id."""


@dataclass(frozen=True, slots=True)
class OutboundMessageIdVO(EntityIdVO):
    """Communication outbound message id."""


@dataclass(frozen=True, slots=True)
class DeliveryAttemptIdVO(EntityIdVO):
    """Communication delivery attempt id."""


@dataclass(frozen=True, slots=True)
class DeliveryEventIdVO(EntityIdVO):
    """Communication delivery event id."""


__all__ = [
    "CommunicationRequestIdVO",
    "DeliveryAttemptIdVO",
    "DeliveryEventIdVO",
    "MessageTemplateIdVO",
    "OutboundMessageIdVO",
    "ProviderConnectionIdVO",
    "ProviderConnectorIdVO",
    "ProviderMessageTypeIdVO",
    "TemplateVersionIdVO",
]
