from __future__ import annotations

from src.modules.communication.domain.error import CommunicationNotFoundError


class ProviderConnectorNotFoundError(CommunicationNotFoundError):
    """Raised when a provider connector is missing."""

    def __init__(self) -> None:
        super().__init__("Provider connector was not found.")


class ProviderMessageTypeNotFoundError(CommunicationNotFoundError):
    """Raised when a provider message type is missing."""

    def __init__(self) -> None:
        super().__init__("Provider message type was not found.")


__all__ = [
    "ProviderConnectorNotFoundError",
    "ProviderMessageTypeNotFoundError",
]
