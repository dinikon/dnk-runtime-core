from __future__ import annotations

from uuid import UUID

import uuid6


class Uuid7Generator:
    """UUID generator implementation based on UUIDv7."""

    def new_uuid(self) -> UUID:
        """Возвращает новый UUIDv7."""
        return uuid6.uuid7()


__all__ = ["Uuid7Generator"]
