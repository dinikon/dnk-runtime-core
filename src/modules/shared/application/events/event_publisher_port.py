from __future__ import annotations

from typing import Protocol

from src.modules.shared.domain.events.integration_event import IntegrationEvent


class EventPublisherPort(Protocol):
    """Port for publishing integration events to an external broker."""

    async def publish(self, event: IntegrationEvent) -> None:
        """Publishes one integration event."""
        ...


__all__ = ["EventPublisherPort"]
