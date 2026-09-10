from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublishOutboxResultDTO:
    """Result of one outbox publication batch."""

    scanned: int
    published: int
    failed: int


__all__ = ["PublishOutboxResultDTO"]
