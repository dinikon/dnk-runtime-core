from __future__ import annotations

from src.modules.communication.domain.error import CommunicationValidationError


class WebhookPayloadValidationError(CommunicationValidationError):
    """Raised when webhook payload cannot be accepted."""


__all__ = ["WebhookPayloadValidationError"]
