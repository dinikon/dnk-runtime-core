from __future__ import annotations

from typing import Any
from uuid import UUID

import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.delivery import HandleProviderWebhookCommand
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.delivery import DeliveryEventIdVO
from src.modules.communication.domain.provider_connector import ProviderConnectorCodeVO
from src.modules.communication.presentation.depends.application import (
    HandleProviderWebhookUseCaseDep,
)
from src.modules.communication.presentation.http.delivery.responses import (
    WebhookResponseSchema,
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
from src.modules.shared.presentation import OptionalRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/communication/webhooks", tags=["communication"])


@router.post(
    "/{tenant_id}/{provider_code}",
    response_model=WebhookResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
)
async def handle_provider_webhook(
    tenant_id: UUID,
    provider_code: str,
    raw_payload: dict[str, Any],
    _context: OptionalRequestContextDep,
    use_case: HandleProviderWebhookUseCaseDep,
) -> WebhookResponseSchema:
    """HTTP endpoint обработки provider webhook."""
    try:
        result = await use_case(
            HandleProviderWebhookCommand(
                tenant_id=EntityIdVO.from_value(tenant_id),
                delivery_event_id=DeliveryEventIdVO.from_value(uuid6.uuid7()),
                provider_code=ProviderConnectorCodeVO(provider_code),
                raw_payload=raw_payload,
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
    return WebhookResponseSchema(
        accepted=result.accepted,
        matched=result.matched,
        outbound_message_id=result.outbound_message_id,
        internal_status=result.internal_status,
    )


__all__ = ["router"]
