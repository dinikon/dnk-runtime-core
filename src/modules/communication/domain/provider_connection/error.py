from __future__ import annotations

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationValidationError,
)


class ProviderConnectionNotFoundError(CommunicationNotFoundError):
    """Raised when a provider connection is missing."""

    def __init__(self) -> None:
        super().__init__("Provider connection was not found.")


class ProviderSecretsValidationError(CommunicationValidationError):
    """Raised when provider secrets are invalid or incomplete."""


__all__ = [
    "ProviderConnectionNotFoundError",
    "ProviderSecretsValidationError",
]
