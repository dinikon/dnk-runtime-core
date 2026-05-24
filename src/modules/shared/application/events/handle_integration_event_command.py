from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HandleIntegrationEventCommand:
    """Command for idempotent integration event consumption."""

    source: str
    message_id: str


__all__ = ["HandleIntegrationEventCommand"]
