from __future__ import annotations

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationValidationError,
)


class InvalidMessageTemplateNameError(CommunicationValidationError):
    """Raised when message template name is invalid."""

    def __init__(self) -> None:
        super().__init__("Message template name cannot be empty.")


class InvalidTemplateVersionTimestampError(CommunicationValidationError):
    """Raised when template version timestamp is invalid."""

    def __init__(self) -> None:
        super().__init__("Template version timestamp must be datetime.")


class MessageTemplateNotFoundError(CommunicationNotFoundError):
    """Raised when a message template is missing."""

    def __init__(self) -> None:
        super().__init__("Message template was not found.")


class TemplateVersionNotFoundError(CommunicationNotFoundError):
    """Raised when a template version is missing."""

    def __init__(self) -> None:
        super().__init__("Template version was not found.")


__all__ = [
    "InvalidMessageTemplateNameError",
    "InvalidTemplateVersionTimestampError",
    "MessageTemplateNotFoundError",
    "TemplateVersionNotFoundError",
]
