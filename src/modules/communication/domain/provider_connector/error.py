from __future__ import annotations

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationValidationError,
)


class ProviderConnectorNotFoundError(CommunicationNotFoundError):
    """Raised when a provider connector is missing."""

    def __init__(self) -> None:
        super().__init__("Provider connector was not found.")


class ProviderConnectorArchivedError(CommunicationValidationError):
    """Raised when archived provider connector is mutated or imported."""

    def __init__(self) -> None:
        super().__init__("Provider connector is archived.")


class ProviderConnectorDeleteForbiddenError(CommunicationValidationError):
    """Raised when provider connector cannot be deleted."""

    def __init__(self) -> None:
        super().__init__("Provider connector must be disabled before deletion.")


class ProviderConnectorInactiveError(CommunicationValidationError):
    """Raised when provider connector cannot be used by dependent objects."""

    def __init__(self) -> None:
        super().__init__("Provider connector is not active.")


class ProviderConnectorStatusTransitionError(CommunicationValidationError):
    """Raised when provider connector status transition is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connector status transition is not allowed.")


class ProviderMessageTypeNotFoundError(CommunicationNotFoundError):
    """Raised when a provider message type is missing."""

    def __init__(self) -> None:
        super().__init__("Provider message type was not found.")


class InvalidProviderConnectorCodeError(CommunicationValidationError):
    """Raised when provider connector code is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connector code is invalid.")


class InvalidProviderConnectorNameError(CommunicationValidationError):
    """Raised when provider connector name is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connector name is invalid.")


class InvalidProviderConnectorVersionError(CommunicationValidationError):
    """Raised when provider connector version is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connector version is invalid.")


class InvalidProviderConnectorTypeError(CommunicationValidationError):
    """Raised when provider connector type is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connector type is invalid.")


class InvalidProviderConnectorStatusError(CommunicationValidationError):
    """Raised when provider connector status is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connector status is invalid.")


class InvalidProviderMessageTypeCodeError(CommunicationValidationError):
    """Raised when provider message type code is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider message type code is invalid.")


class InvalidProviderMessageTypeNameError(CommunicationValidationError):
    """Raised when provider message type name is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider message type name is invalid.")


class InvalidProviderChannelCodeError(CommunicationValidationError):
    """Raised when provider channel code is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider channel code is invalid.")


__all__ = [
    "InvalidProviderChannelCodeError",
    "InvalidProviderConnectorCodeError",
    "InvalidProviderConnectorNameError",
    "InvalidProviderConnectorStatusError",
    "InvalidProviderConnectorTypeError",
    "InvalidProviderConnectorVersionError",
    "InvalidProviderMessageTypeCodeError",
    "InvalidProviderMessageTypeNameError",
    "ProviderConnectorArchivedError",
    "ProviderConnectorDeleteForbiddenError",
    "ProviderConnectorInactiveError",
    "ProviderConnectorNotFoundError",
    "ProviderConnectorStatusTransitionError",
    "ProviderMessageTypeNotFoundError",
]
