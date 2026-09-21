from uuid import uuid4
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)
from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CurrencyEventWriter:
    """Append tenant changes to the transaction's shared outbox."""

    def __init__(self, outbox: OutboxRepositoryProtocol, clock: ClockPort):
        self.outbox, self.clock = outbox, clock

    async def publish(
        self,
        tenant_id: EntityIdVO,
        actor_id: EntityIdVO,
        name: str,
        payload: dict[str, object],
        aggregate_id: EntityIdVO | None = None,
    ) -> None:
        """Record an event in the caller's UnitOfWork without committing."""
        await self.outbox.add(
            IntegrationEvent(
                uuid4(),
                tenant_id.uuid,
                name,
                1,
                "currency",
                (aggregate_id or tenant_id).uuid,
                {"actor_id": str(actor_id), **payload},
                self.clock.now(),
            )
        )


__all__ = ["CurrencyEventWriter"]
