from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.communication.application.outbound_message import (
    SendCommunicationCommand,
    SendCommunicationResultDTO,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageStatus,
)
from src.modules.communication.presentation.depends.application import (
    CommunicationRepositoryDep,
    GetOutboundMessageUseCaseDep,
    ListOutboundMessagesUseCaseDep,
    OutboundMessagePublisherDep,
    SendCommunicationUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.runtime_data import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared.depends import AuthenticatedRequestContextDep, UoWDep
from src.modules.shared.domain.errors import DomainError

log = logging.getLogger(__name__)

router = APIRouter(prefix="/communication", tags=["communication"])


class SendCommunicationRequestSchema(BaseModel):
    initiator_type: str
    message_class: str
    channel_code: str
    recipient_address: str
    template_code: str | None = None
    template_id: UUID | None = None
    initiator_ref_id: str | None = None
    correlation_id: UUID | None = None
    idempotency_key: str | None = None
    contact_id: UUID | None = None
    recipient_snapshot: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


class SendCommunicationResponseSchema(BaseModel):
    communication_request_id: UUID
    outbound_message_id: UUID
    status: str
    internal_status: str
    idempotent: bool


class OutboundMessageResponseSchema(BaseModel):
    outbound_message_id: UUID
    tenant_id: UUID
    communication_request_id: UUID
    provider_connection_id: UUID
    channel_code: str
    contact_id: UUID | None
    recipient_address: str
    rendered_payload: dict[str, Any]
    provider_request_payload: dict[str, Any]
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    error_code: str | None
    error_message: str | None
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ListOutboundMessagesResponseSchema(BaseModel):
    items: list[OutboundMessageResponseSchema]


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
    repository: CommunicationRepositoryDep,
    publisher: OutboundMessagePublisherDep,
) -> SendCommunicationResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            SendCommunicationCommand(
                tenant_id=tenant_id,
                initiator_type=payload.initiator_type,
                message_class=payload.message_class,
                channel_code=payload.channel_code,
                recipient_address=payload.recipient_address,
                template_code=payload.template_code,
                template_id=payload.template_id,
                initiator_ref_id=payload.initiator_ref_id,
                correlation_id=payload.correlation_id,
                idempotency_key=payload.idempotency_key,
                contact_id=payload.contact_id,
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
    except CommunicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
        CommunicationRuntimeStateError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        CommunicationValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
        DomainError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return SendCommunicationResponseSchema(
        communication_request_id=result.communication_request_id,
        outbound_message_id=result.outbound_message_id,
        status=result.status,
        internal_status=result.internal_status,
        idempotent=result.idempotent,
    )


@router.get("/messages", response_model=ListOutboundMessagesResponseSchema)
async def list_messages(
    context: AuthenticatedRequestContextDep,
    use_case: ListOutboundMessagesUseCaseDep,
    limit: int = 100,
    offset: int = 0,
) -> ListOutboundMessagesResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        items = await use_case(tenant_id=tenant_id, limit=limit, offset=offset)
    except CommunicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
        CommunicationRuntimeStateError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        CommunicationValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
        DomainError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ListOutboundMessagesResponseSchema(
        items=[
            OutboundMessageResponseSchema(
                outbound_message_id=item.outbound_message_id,
                tenant_id=item.tenant_id,
                communication_request_id=item.communication_request_id,
                provider_connection_id=item.provider_connection_id,
                channel_code=item.channel_code,
                contact_id=item.contact_id,
                recipient_address=item.recipient_address,
                rendered_payload=dict(item.rendered_payload),
                provider_request_payload=dict(item.provider_request_payload),
                external_message_id=item.external_message_id,
                external_status=item.external_status,
                internal_status=item.internal_status,
                error_code=item.error_code,
                error_message=item.error_message,
                queued_at=item.queued_at,
                sent_at=item.sent_at,
                delivered_at=item.delivered_at,
                failed_at=item.failed_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


@router.get(
    "/messages/{outbound_message_id}",
    response_model=OutboundMessageResponseSchema,
)
async def get_message(
    outbound_message_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetOutboundMessageUseCaseDep,
) -> OutboundMessageResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
        )
    except CommunicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
        CommunicationRuntimeStateError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        CommunicationValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
        DomainError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return OutboundMessageResponseSchema(
        outbound_message_id=result.outbound_message_id,
        tenant_id=result.tenant_id,
        communication_request_id=result.communication_request_id,
        provider_connection_id=result.provider_connection_id,
        channel_code=result.channel_code,
        contact_id=result.contact_id,
        recipient_address=result.recipient_address,
        rendered_payload=dict(result.rendered_payload),
        provider_request_payload=dict(result.provider_request_payload),
        external_message_id=result.external_message_id,
        external_status=result.external_status,
        internal_status=result.internal_status,
        error_code=result.error_code,
        error_message=result.error_message,
        queued_at=result.queued_at,
        sent_at=result.sent_at,
        delivered_at=result.delivered_at,
        failed_at=result.failed_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


async def _publish_send_job_after_commit(
    *,
    tenant_id: UUID,
    result: SendCommunicationResultDTO,
    repository: CommunicationRepositoryDep,
    publisher: OutboundMessagePublisherDep,
    uow: UoWDep,
) -> None:
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
    "ListOutboundMessagesResponseSchema",
    "OutboundMessageResponseSchema",
    "SendCommunicationRequestSchema",
    "SendCommunicationResponseSchema",
    "_publish_send_job_after_commit",
    "router",
]
