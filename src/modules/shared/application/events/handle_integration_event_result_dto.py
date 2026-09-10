from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HandleIntegrationEventResultDTO:
    """Result of idempotent event consumption."""

    consumed: bool
    duplicate: bool


__all__ = ["HandleIntegrationEventResultDTO"]
