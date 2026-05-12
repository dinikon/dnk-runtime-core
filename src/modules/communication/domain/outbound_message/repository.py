from __future__ import annotations

from typing import Protocol


class OutboundMessageRepositoryProtocol(Protocol):
    """Repository protocol marker for outbound message aggregate."""


__all__ = ["OutboundMessageRepositoryProtocol"]
