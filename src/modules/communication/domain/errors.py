from __future__ import annotations


class CommunicationError(Exception):
    """Base communication module error."""


class CommunicationValidationError(CommunicationError):
    """Raised when a communication payload or provider contract is invalid."""


class CommunicationNotFoundError(CommunicationError):
    """Raised when a requested communication object is missing."""


__all__ = [
    "CommunicationError",
    "CommunicationNotFoundError",
    "CommunicationValidationError",
]
