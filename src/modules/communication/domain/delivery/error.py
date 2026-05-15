from __future__ import annotations

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationValidationError,
)


class WebhookPayloadValidationError(CommunicationValidationError):
    """Raised when webhook payload cannot be accepted."""


class InvalidExternalMessageIdError(WebhookPayloadValidationError):
    """Raised when provider external message id is empty."""


class DeliveryAttemptNotFoundError(CommunicationNotFoundError):
    """Raised when delivery attempt cannot be found."""


__all__ = [
    "DeliveryAttemptNotFoundError",
    "InvalidExternalMessageIdError",
    "WebhookPayloadValidationError",
]
