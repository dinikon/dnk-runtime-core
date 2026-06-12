from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class GetBroadcastRequestSchema(BaseModel):
    """Pydantic-схема публичного чтения broadcast."""

    id: UUID


__all__ = ["GetBroadcastRequestSchema"]
