from __future__ import annotations

from datetime import UTC, datetime
import logging
from uuid import UUID

from fastapi import APIRouter, status
import uuid6

from src.modules.communication.application.outbound_message import (
    SendCommunicationCommand,
    SendCommunicationResultDTO,
)
from src.modules.communication.domain.message_template import MessageTemplateIdVO
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
    OutboundMessageStatus,
)
from src.modules.communication.presentation.depends.application import (
    OutboundMessagePublisherDep,
    SendCommunicationUseCaseDep,
)
from src.modules.communication.presentation.depends.infrastructure import (
    OutboundMessageRuntimeRepositoryDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.outbound_message.controller.error_mapper import (
    map_outbound_http_error,
)
from src.modules.communication.presentation.http.outbound_message.requests import (
    SendCommunicationRequestSchema,
)
from src.modules.communication.presentation.http.outbound_message.responses import (
    SendCommunicationResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep, UoWDep

log = logging.getLogger(__name__)

router = APIRouter(prefix="/communication", tags=["communication"])


@router.post(
    "/send",
    response_model=SendCommunicationResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_communication(
    payload: SendCommunicationRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: SendCommunicationUseCaseDep,
    uow: UoWDep,
    repository: OutboundMessageRuntimeRepositoryDep,
    publisher: OutboundMessagePublisherDep,
) -> SendCommunicationResponseSchema:
    """HTTP controller постановки outbound message на отправку."""
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            SendCommunicationCommand(
                tenant_id=EntityIdVO.from_value(tenant_id),
                communication_request_id=CommunicationRequestIdVO.from_value(
                    uuid6.uuid7()
                ),
                outbound_message_id=OutboundMessageIdVO.from_value(uuid6.uuid7()),
                initiator_type=payload.initiator_type,
                message_class=payload.message_class,
                channel_code=payload.channel_code,
                recipient_address=payload.recipient_address,
                template_code=payload.template_code,
                template_id=(
                    None
                    if payload.template_id is None
                    else MessageTemplateIdVO.from_value(payload.template_id)
                ),
                initiator_ref_id=payload.initiator_ref_id,
                correlation_id=(
                    None
                    if payload.correlation_id is None
                    else EntityIdVO.from_value(payload.correlation_id)
                ),
                idempotency_key=payload.idempotency_key,
                contact_id=(
                    None
                    if payload.contact_id is None
                    else EntityIdVO.from_value(payload.contact_id)
                ),
                recipient_snapshot=payload.recipient_snapshot,
                variables=payload.variables,
                scheduled_at=payload.scheduled_at,
                priority=payload.priority,
            )
        )
        await uow.commit()
        await _publish_send_job_after_commit(
            tenant_id=tenant_id,
            result=result,
            repository=repository,
            publisher=publisher,
            uow=uow,
        )
    except Exception as exc:
        raise map_outbound_http_error(exc) from exc
    return SendCommunicationResponseSchema(
        communication_request_id=result.communication_request_id,
        outbound_message_id=result.outbound_message_id,
        status=result.status,
        internal_status=result.internal_status,
        idempotent=result.idempotent,
    )


async def _publish_send_job_after_commit(
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


__all__ = [
    "SendCommunicationRequestSchema",
    "SendCommunicationResponseSchema",
    "_publish_send_job_after_commit",
    "router",
    "send_communication",
]
