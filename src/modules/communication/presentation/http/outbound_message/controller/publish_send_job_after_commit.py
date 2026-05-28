from __future__ import annotations

from datetime import UTC, datetime
import logging
from uuid import UUID

from src.modules.communication.application.outbound_message import (
    SendCommunicationResultDTO,
)
from src.modules.communication.domain.outbound_message import OutboundMessageStatus
from src.modules.communication.presentation.depends.application import (
    OutboundMessagePublisherDep,
)
from src.modules.shared.presentation import UoWDep

log = logging.getLogger(__name__)


async def publish_send_job_after_commit(
    *,
    tenant_id: UUID,
    result: SendCommunicationResultDTO,
    repository,
    publisher: OutboundMessagePublisherDep,
    uow: UoWDep,
) -> None:
    """Публикует queued outbound job после успешного commit send operation."""
    if publisher is None:
        return
    if result.internal_status != OutboundMessageStatus.QUEUED.value:
        return

    published_at = datetime.now(UTC)
    try:
        await publisher.publish(
            tenant_id=tenant_id,
            outbound_message_id=result.outbound_message_id,
            published_at=published_at,
            source="send_communication",
        )
        await repository.mark_outbound_published(
            tenant_id=tenant_id,
            outbound_message_id=result.outbound_message_id,
            published_at=published_at,
        )
        await uow.commit()
    except Exception:
        await uow.rollback()
        log.warning(
            "Failed to publish outbound communication message after send commit.",
            extra={"outbound_message_id": str(result.outbound_message_id)},
            exc_info=True,
        )


__all__ = ["publish_send_job_after_commit"]
