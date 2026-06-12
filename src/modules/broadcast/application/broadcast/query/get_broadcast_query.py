from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetBroadcastQuery:
    """Query чтения одной broadcast definition tenant."""

    tenant_id: UUID | str
    broadcast_id: UUID | str


__all__ = ["GetBroadcastQuery"]
