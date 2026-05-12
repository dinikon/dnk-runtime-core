from __future__ import annotations

from typing import Protocol


class DeliveryRepositoryProtocol(Protocol):
    """Repository protocol marker for delivery aggregate."""


__all__ = ["DeliveryRepositoryProtocol"]
