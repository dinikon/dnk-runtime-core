from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.communication.application.delivery import ListDeliveryEventsQuery
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.presentation.depends.application import (
    ListDeliveryEventsUseCaseDep,
)
from src.modules.communication.presentation.http.delivery.requests import (
    ListMessageDeliveryEventsRequestSchema,
)
from src.modules.communication.presentation.http.delivery.responses import (
    DeliveryEventResponseSchema,
    ListDeliveryEventsResponseSchema,
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
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get(
    "/messages/{outbound_message_id}/events",
    response_model=ListDeliveryEventsResponseSchema,
)
async def list_message_delivery_events(
    outbound_message_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryEventsUseCaseDep,
    request: ListMessageDeliveryEventsRequestSchema = Depends(),
) -> ListDeliveryEventsResponseSchema:
    """HTTP controller списка delivery events по outbound message."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = principal.tenant_id
    try:
        items = await use_case(
            ListDeliveryEventsQuery(
                tenant_id=EntityIdVO.from_value(tenant_id),
                limit=request.limit,
                offset=request.offset,
                outbound_message_id=OutboundMessageIdVO.from_value(outbound_message_id),
                external_message_id=None,
                internal_status=None,
                event_type=None,
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
    return ListDeliveryEventsResponseSchema(
        items=[
            DeliveryEventResponseSchema(
                delivery_event_id=item.delivery_event_id,
                tenant_id=item.tenant_id,
                outbound_message_id=item.outbound_message_id,
                provider_connection_id=item.provider_connection_id,
                external_message_id=item.external_message_id,
                external_status=item.external_status,
                internal_status=item.internal_status,
                event_type=item.event_type,
                event_at=item.event_at,
                raw_payload=dict(item.raw_payload),
                created_at=item.created_at,
            )
            for item in items
        ]
    )


__all__ = ["list_message_delivery_events", "router"]
