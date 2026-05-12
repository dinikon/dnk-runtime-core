from __future__ import annotations

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationValidationError,
)


class OutboundMessageNotFoundError(CommunicationNotFoundError):
    """Raised when an outbound message is missing."""

    def __init__(self) -> None:
        super().__init__("Outbound message was not found.")


class ProviderPayloadValidationError(CommunicationValidationError):
    """Raised when provider payload rendering or mapping is invalid."""


__all__ = [
    "OutboundMessageNotFoundError",
    "ProviderPayloadValidationError",
]
