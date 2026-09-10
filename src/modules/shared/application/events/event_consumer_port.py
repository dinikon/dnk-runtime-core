from __future__ import annotations

from typing import Protocol

from src.modules.shared.domain.events.integration_event import IntegrationEvent


class EventConsumerPort(Protocol):
    """Port implemented by business integration-event handlers."""

    async def handle(self, event: IntegrationEvent) -> None:
        """Handles one integration event."""
        ...


__all__ = ["EventConsumerPort"]
