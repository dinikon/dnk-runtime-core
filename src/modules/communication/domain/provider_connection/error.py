from __future__ import annotations

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationValidationError,
)


class ProviderConnectionNotFoundError(CommunicationNotFoundError):
    """Raised when a provider connection is missing."""

    def __init__(self) -> None:
        super().__init__("Provider connection was not found.")


class InvalidProviderConnectionCodeError(CommunicationValidationError):
    """Raised when provider connection code is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connection code cannot be empty.")


class InvalidProviderConnectionNameError(CommunicationValidationError):
    """Raised when provider connection name is invalid."""

    def __init__(self) -> None:
        super().__init__("Provider connection name cannot be empty.")


class ProviderSecretsValidationError(CommunicationValidationError):
    """Raised when provider secrets are invalid or incomplete."""


__all__ = [
    "InvalidProviderConnectionCodeError",
    "InvalidProviderConnectionNameError",
    "ProviderConnectionNotFoundError",
    "ProviderSecretsValidationError",
]
