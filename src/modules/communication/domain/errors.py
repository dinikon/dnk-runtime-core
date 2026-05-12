from __future__ import annotations

from src.modules.shared.domain.errors import DomainError


class CommunicationError(DomainError):
    """Base communication module error."""


class CommunicationValidationError(CommunicationError):
    """Raised when a communication payload or provider contract is invalid."""


class CommunicationNotFoundError(CommunicationError):
    """Raised when a requested communication object is missing."""


class CommunicationRuntimeStateError(CommunicationError):
    """Raised when communication runtime state is inconsistent or unavailable."""


class ProviderConnectorNotFoundError(CommunicationNotFoundError):
    """Raised when a provider connector is missing."""

    def __init__(self) -> None:
        super().__init__("Provider connector was not found.")


class ProviderMessageTypeNotFoundError(CommunicationNotFoundError):
    """Raised when a provider message type is missing."""

    def __init__(self) -> None:
        super().__init__("Provider message type was not found.")


class ProviderConnectionNotFoundError(CommunicationNotFoundError):
    """Raised when a provider connection is missing."""

    def __init__(self) -> None:
        super().__init__("Provider connection was not found.")


class MessageTemplateNotFoundError(CommunicationNotFoundError):
    """Raised when a message template is missing."""

    def __init__(self) -> None:
        super().__init__("Message template was not found.")


class TemplateVersionNotFoundError(CommunicationNotFoundError):
    """Raised when a template version is missing."""

    def __init__(self) -> None:
        super().__init__("Template version was not found.")


class OutboundMessageNotFoundError(CommunicationNotFoundError):
    """Raised when an outbound message is missing."""

    def __init__(self) -> None:
        super().__init__("Outbound message was not found.")


class ProviderPayloadValidationError(CommunicationValidationError):
    """Raised when provider payload rendering or mapping is invalid."""


class ProviderSecretsValidationError(CommunicationValidationError):
    """Raised when provider secrets are invalid or incomplete."""


class WebhookPayloadValidationError(CommunicationValidationError):
    """Raised when webhook payload cannot be accepted."""


__all__ = [
    "CommunicationError",
    "CommunicationNotFoundError",
    "CommunicationRuntimeStateError",
    "CommunicationValidationError",
    "MessageTemplateNotFoundError",
    "OutboundMessageNotFoundError",
    "ProviderConnectionNotFoundError",
    "ProviderConnectorNotFoundError",
    "ProviderMessageTypeNotFoundError",
    "ProviderPayloadValidationError",
    "ProviderSecretsValidationError",
    "TemplateVersionNotFoundError",
    "WebhookPayloadValidationError",
]
