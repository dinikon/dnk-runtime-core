from __future__ import annotations

from datetime import datetime
from uuid import UUID

import uuid6
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.infrastructure.inbox.persistence import (
    IntegrationInboxEventModel,
)
from src.modules.shared.kernel.events import (
    InboxEventStatus,
    IntegrationEvent,
)


class SqlAlchemyInboxRepository:
    """SQLAlchemy-backed inbox repository for idempotent consumers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_received(
        self,
        *,
        source: str,
        message_id: str,
        event: IntegrationEvent,
        received_at: datetime,
    ) -> bool:
        """Records a delivery and returns False when it is a duplicate."""
        stmt = (
            insert(IntegrationInboxEventModel)
            .values(
                id=uuid6.uuid7(),
                tenant_id=event.tenant_id,
                source=source,
                message_id=message_id,
                event_type=event.event_type,
                consumed_at=None,
                status=InboxEventStatus.RECEIVED.value,
                error=None,
                created_at=received_at,
                updated_at=received_at,
            )
            .on_conflict_do_nothing(
                index_elements=["tenant_id", "source", "message_id"]
            )
            .returning(IntegrationInboxEventModel.id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none() is not None

    async def mark_consumed(
        self,
        *,
        tenant_id: UUID,
        source: str,
        message_id: str,
        consumed_at: datetime,
    ) -> None:
        """Marks a delivery as consumed."""
        await self._session.execute(
            update(IntegrationInboxEventModel)
            .where(IntegrationInboxEventModel.tenant_id == tenant_id)
            .where(IntegrationInboxEventModel.source == source)
            .where(IntegrationInboxEventModel.message_id == message_id)
            .values(
                consumed_at=consumed_at,
                status=InboxEventStatus.CONSUMED.value,
                error=None,
            )
        )
        await self._session.flush()

    async def mark_failed(
        self,
        *,
        tenant_id: UUID,
        source: str,
        message_id: str,
        error: str,
    ) -> None:
        """Stores a handler failure for a delivery."""
        await self._session.execute(
            update(IntegrationInboxEventModel)
            .where(IntegrationInboxEventModel.tenant_id == tenant_id)
            .where(IntegrationInboxEventModel.source == source)
            .where(IntegrationInboxEventModel.message_id == message_id)
            .values(
                status=InboxEventStatus.FAILED.value,
                error=error,
            )
        )
        await self._session.flush()


__all__ = ["SqlAlchemyInboxRepository"]
