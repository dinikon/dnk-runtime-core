from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from src.modules.communication.application.delivery import ListDeliveryAttemptsQuery
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.communication.presentation.depends.application import (
    ListDeliveryAttemptsUseCaseDep,
)
from src.modules.communication.presentation.http.common import (
    map_communication_http_error,
    require_tenant_id,
)
from src.modules.communication.presentation.http.delivery.responses import (
    DeliveryAttemptResponseSchema,
    ListDeliveryAttemptsResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get(
    "/messages/{outbound_message_id}/attempts",
    response_model=ListDeliveryAttemptsResponseSchema,
)
async def list_message_delivery_attempts(
    outbound_message_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryAttemptsUseCaseDep,
    limit: int = 100,
    offset: int = 0,
) -> ListDeliveryAttemptsResponseSchema:
    """HTTP controller списка delivery attempts по outbound message."""
    return await _list_delivery_attempts(
        context=context,
        use_case=use_case,
        limit=limit,
        offset=offset,
        outbound_message_id=outbound_message_id,
        status=None,
    )


@router.get(
    "/delivery-attempts",
    response_model=ListDeliveryAttemptsResponseSchema,
)
async def list_delivery_attempts(
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryAttemptsUseCaseDep,
    outbound_message_id: UUID | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ListDeliveryAttemptsResponseSchema:
    """HTTP controller списка delivery attempts."""
    return await _list_delivery_attempts(
        context=context,
        use_case=use_case,
        limit=limit,
        offset=offset,
        outbound_message_id=outbound_message_id,
        status=status,
    )


async def _list_delivery_attempts(
    *,
    context: AuthenticatedRequestContextDep,
    use_case: ListDeliveryAttemptsUseCaseDep,
    limit: int,
    offset: int,
    outbound_message_id: UUID | None,
    status: str | None,
) -> ListDeliveryAttemptsResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        items = await use_case(
            ListDeliveryAttemptsQuery(
                tenant_id=EntityIdVO.from_value(tenant_id),
                limit=limit,
                offset=offset,
                outbound_message_id=(
                    None
                    if outbound_message_id is None
                    else OutboundMessageIdVO.from_value(outbound_message_id)
                ),
                status=status,
            )
        )
    except Exception as exc:
        raise map_communication_http_error(exc) from exc
    return ListDeliveryAttemptsResponseSchema(
        items=[
            DeliveryAttemptResponseSchema(
                delivery_attempt_id=item.delivery_attempt_id,
                tenant_id=item.tenant_id,
                outbound_message_id=item.outbound_message_id,
                provider_connection_id=item.provider_connection_id,
                attempt_no=item.attempt_no,
                status=item.status,
                request_payload=(
                    None if item.request_payload is None else dict(item.request_payload)
                ),
                response_payload=(
                    None
                    if item.response_payload is None
                    else dict(item.response_payload)
                ),
                http_status_code=item.http_status_code,
                external_message_id=item.external_message_id,
                error_code=item.error_code,
                error_message=item.error_message,
                started_at=item.started_at,
                finished_at=item.finished_at,
            )
            for item in items
        ]
    )


__all__ = [
    "list_delivery_attempts",
    "list_message_delivery_attempts",
    "router",
]
