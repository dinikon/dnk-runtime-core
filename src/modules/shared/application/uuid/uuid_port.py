from __future__ import annotations

from typing import Protocol
from uuid import UUID


class UUIdGeneratorProtocol(Protocol):
    """Порт генерации UUID."""

    def new(self) -> UUID:
        """Возвращает новый UUID."""
        ...


__all__ = ["UUIdGeneratorProtocol"]
