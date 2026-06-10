from __future__ import annotations

import uuid

from src.modules.shared.application.uuid import UUIdGeneratorProtocol


class UUID7Generator(UUIdGeneratorProtocol):
    """UUID generator implementation based on UUIDv7."""

    def new(self) -> uuid.UUID:
        """Возвращает новый UUIDv7."""
        return uuid.uuid7()


__all__ = ["UUID7Generator"]
