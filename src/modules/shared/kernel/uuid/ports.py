from __future__ import annotations

from typing import Protocol
from uuid import UUID


class UuidPort(Protocol):
    """Порт генерации UUID."""

    def new_uuid(self) -> UUID:
        """Возвращает новый UUID."""
        ...


__all__ = ["UuidPort"]
