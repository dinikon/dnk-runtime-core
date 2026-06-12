from __future__ import annotations

import uuid
import uuid6

from src.modules.shared.application.uuid import UUIdGeneratorProtocol


class UUID7Generator(UUIdGeneratorProtocol):
    """UUID generator implementation based on UUIDv7."""

    def new(self) -> uuid.UUID:
        """Возвращает новый UUIDv7."""
        return uuid6.uuid7()


__all__ = ["UUID7Generator"]
