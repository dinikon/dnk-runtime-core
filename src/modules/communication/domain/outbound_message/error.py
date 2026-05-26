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


class InvalidInitiatorTypeError(CommunicationValidationError):
    """Raised when communication request initiator type is invalid."""

    def __init__(self) -> None:
        super().__init__("Communication initiator type is invalid.")


class InvalidRecipientAddressError(CommunicationValidationError):
    """Raised when outbound recipient address is invalid."""

    def __init__(self) -> None:
        super().__init__("Outbound recipient address is invalid.")


class InvalidRecipientIdentifierTypeError(CommunicationValidationError):
    """Raised when recipient identifier type is invalid."""

    def __init__(self) -> None:
        super().__init__("Recipient identifier type is invalid.")


class InvalidOutboundPriorityError(CommunicationValidationError):
    """Raised when outbound priority is invalid."""

    def __init__(self) -> None:
        super().__init__("Outbound priority is invalid.")


class InvalidIdempotencyKeyError(CommunicationValidationError):
    """Raised when communication idempotency key is invalid."""

    def __init__(self) -> None:
        super().__init__("Communication idempotency key is invalid.")


__all__ = [
    "InvalidIdempotencyKeyError",
    "InvalidInitiatorTypeError",
    "InvalidOutboundPriorityError",
    "InvalidRecipientAddressError",
    "InvalidRecipientIdentifierTypeError",
    "OutboundMessageNotFoundError",
    "ProviderPayloadValidationError",
]
