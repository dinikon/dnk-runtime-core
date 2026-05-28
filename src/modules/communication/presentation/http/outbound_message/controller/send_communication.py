from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
import uuid6

from src.modules.communication.application.outbound_message import (
    SendCommunicationCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.message_template import MessageTemplateIdVO
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
)
from src.modules.communication.presentation.depends.application import (
    OutboundMessagePublisherDep,
    SendCommunicationUseCaseDep,
)
from src.modules.communication.presentation.depends.infrastructure import (
    OutboundMessageRuntimeRepositoryDep,
)
from src.modules.communication.presentation.http.outbound_message.requests import (
    SendCommunicationRequestSchema,
)
from src.modules.communication.presentation.http.outbound_message.responses import (
    SendCommunicationResponseSchema,
)
from src.modules.communication.presentation.http.outbound_message.controller.publish_send_job_after_commit import (
    publish_send_job_after_commit,
)
from src.modules.runtime_data.domain.error import (
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
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep, UoWDep

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
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = principal.tenant_id
    try:
        result = await use_case(
            SendCommunicationCommand(
                tenant_id=EntityIdVO.from_value(tenant_id),
                communication_request_id=CommunicationRequestIdVO.from_value(
                    uuid6.uuid7()
                ),
                outbound_message_id=OutboundMessageIdVO.from_value(uuid6.uuid7()),
                initiator_type=payload.initiator_type,
                initiator_ref_id=payload.initiator_ref_id,
                correlation_id=EntityIdVO.from_value(payload.correlation_id),
                idempotency_key=payload.idempotency_key,
                channel_code=payload.channel_code,
                template_id=MessageTemplateIdVO.from_value(payload.template_id),
                recipient_identifier_type=payload.recipient_identifier_type,
                recipient_address=payload.recipient_address,
                recipient_snapshot=payload.recipient_snapshot,
                message_class=payload.message_class,
                variables=payload.variables,
                scheduled_at=payload.scheduled_at,
                priority=payload.priority,
            )
        )
        await uow.commit()
        await publish_send_job_after_commit(
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


__all__ = [
    "SendCommunicationRequestSchema",
    "SendCommunicationResponseSchema",
    "router",
    "send_communication",
]
