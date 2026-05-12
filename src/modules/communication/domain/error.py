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


__all__ = [
    "CommunicationError",
    "CommunicationNotFoundError",
    "CommunicationRuntimeStateError",
    "CommunicationValidationError",
]

