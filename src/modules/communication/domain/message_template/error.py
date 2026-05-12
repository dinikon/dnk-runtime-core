from __future__ import annotations

from src.modules.communication.domain.error import CommunicationNotFoundError


class MessageTemplateNotFoundError(CommunicationNotFoundError):
    """Raised when a message template is missing."""

    def __init__(self) -> None:
        super().__init__("Message template was not found.")


class TemplateVersionNotFoundError(CommunicationNotFoundError):
    """Raised when a template version is missing."""

    def __init__(self) -> None:
        super().__init__("Template version was not found.")


__all__ = [
    "MessageTemplateNotFoundError",
    "TemplateVersionNotFoundError",
]
