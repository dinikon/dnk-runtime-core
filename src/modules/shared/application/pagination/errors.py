from src.modules.shared import DomainError


class InvalidCursorError(DomainError):
    """Raised when an opaque pagination cursor cannot be decoded."""


__all__ = ["InvalidCursorError"]
