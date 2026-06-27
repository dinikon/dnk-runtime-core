from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.outbound_message import (
    ListOutboundMessagesQuery,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    ListOutboundMessagesUseCaseDep,
)
from src.modules.communication.presentation.http.outbound_message.responses import (
    ListOutboundMessagesResponseSchema,
    OutboundMessageResponseSchema,
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
from src.modules.shared import DomainError
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get("/messages", response_model=ListOutboundMessagesResponseSchema)
async def list_messages(
    context: AuthenticatedRequestContextDep,
    use_case: ListOutboundMessagesUseCaseDep,
    limit: int = 100,
    offset: int = 0,
) -> ListOutboundMessagesResponseSchema:
    """HTTP controller списка outbound messages."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = principal.tenant_id
    try:
        items = await use_case(
            ListOutboundMessagesQuery(
                tenant_id=EntityIdVO.from_value(tenant_id),
                limit=limit,
                offset=offset,
            )
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
    return ListOutboundMessagesResponseSchema(
        items=[
            OutboundMessageResponseSchema(
                outbound_message_id=item.outbound_message_id,
                tenant_id=item.tenant_id,
                communication_request_id=item.communication_request_id,
                provider_connection_id=item.provider_connection_id,
                channel_code=item.channel_code,
                recipient_identifier_type=item.recipient_identifier_type,
                recipient_address=item.recipient_address,
                recipient_snapshot=dict(item.recipient_snapshot),
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


__all__ = ["list_messages", "router"]
