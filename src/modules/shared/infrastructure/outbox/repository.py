from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.infrastructure.outbox.persistence import (
    IntegrationOutboxEventModel,
)
from src.modules.shared.kernel.events import (
    IntegrationEvent,
    OutboxEvent,
    OutboxEventStatus,
)


class SqlAlchemyOutboxRepository:
    """SQLAlchemy-backed integration outbox repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: IntegrationEvent) -> None:
        """Adds an integration event to the current UnitOfWork."""
        self._session.add(
            IntegrationOutboxEventModel(
                id=event.event_id,
                tenant_id=event.tenant_id,
                event_type=event.event_type,
                event_version=event.event_version,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                payload=dict(event.payload),
                occurred_at=event.occurred_at,
                published_at=None,
                publish_attempts=0,
                status=OutboxEventStatus.PENDING.value,
                next_attempt_at=None,
                last_error=None,
            )
        )
        await self._session.flush()

    async def claim_due_events(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> list[OutboxEvent]:
        """Claims pending events due for publication."""
        if limit <= 0:
            return []

        models = list(
            (
                await self._session.scalars(
                    select(IntegrationOutboxEventModel)
                    .where(
                        IntegrationOutboxEventModel.status
                        == OutboxEventStatus.PENDING.value
                    )
                    .where(
                        or_(
                            IntegrationOutboxEventModel.next_attempt_at.is_(None),
                            IntegrationOutboxEventModel.next_attempt_at <= now,
                        )
                    )
                    .order_by(
                        IntegrationOutboxEventModel.occurred_at,
                        IntegrationOutboxEventModel.id,
                    )
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for model in models:
            model.status = OutboxEventStatus.PUBLISHING.value
            model.publish_attempts = int(model.publish_attempts or 0) + 1
            model.next_attempt_at = None
        await self._session.flush()
        return [_outbox_event(model) for model in models]

    async def mark_published(
        self,
        *,
        event_id: UUID,
        published_at: datetime,
    ) -> None:
        """Marks one claimed event as published."""
        await self._session.execute(
            update(IntegrationOutboxEventModel)
            .where(IntegrationOutboxEventModel.id == event_id)
            .values(
                status=OutboxEventStatus.PUBLISHED.value,
                published_at=published_at,
                next_attempt_at=None,
                last_error=None,
            )
        )
        await self._session.flush()

    async def mark_publish_failed(
        self,
        *,
        event_id: UUID,
        error: str,
        next_attempt_at: datetime | None,
    ) -> None:
        """Marks one claimed event as pending retry or terminally failed."""
        status = (
            OutboxEventStatus.FAILED.value
            if next_attempt_at is None
            else OutboxEventStatus.PENDING.value
        )
        await self._session.execute(
            update(IntegrationOutboxEventModel)
            .where(IntegrationOutboxEventModel.id == event_id)
            .values(
                status=status,
                next_attempt_at=next_attempt_at,
                last_error=error,
            )
        )
        await self._session.flush()


def _outbox_event(model: IntegrationOutboxEventModel) -> OutboxEvent:
    return OutboxEvent(
        id=model.id,
        tenant_id=model.tenant_id,
        event_type=model.event_type,
        event_version=model.event_version,
        aggregate_type=model.aggregate_type,
        aggregate_id=model.aggregate_id,
        payload=dict(model.payload or {}),
        occurred_at=model.occurred_at,
        published_at=model.published_at,
        publish_attempts=int(model.publish_attempts or 0),
        status=model.status,
        next_attempt_at=model.next_attempt_at,
        last_error=model.last_error,
    )


__all__ = ["SqlAlchemyOutboxRepository"]
