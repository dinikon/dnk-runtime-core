from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.provider_connection import (
    UpdateProviderConnectionStatusCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.presentation.depends.application import (
    UpdateProviderConnectionStatusUseCaseDep,
)
from src.modules.communication.presentation.http.provider_connection.requests import (
    UpdateProviderConnectionStatusRequestSchema,
)
from src.modules.communication.presentation.http.provider_connection.responses import (
    ProviderConnectionResponseSchema,
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

router = APIRouter(prefix="/communication/providers", tags=["communication"])


@router.patch(
    "/connections/{provider_connection_id}/status",
    response_model=ProviderConnectionResponseSchema,
)
async def update_provider_connection_status(
    provider_connection_id: UUID,
    payload: UpdateProviderConnectionStatusRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateProviderConnectionStatusUseCaseDep,
) -> ProviderConnectionResponseSchema:
    """HTTP endpoint смены статуса provider connection текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await use_case(
            UpdateProviderConnectionStatusCommand(
                tenant_id=tenant_id,
                provider_connection_id=ProviderConnectionIdVO.from_value(
                    provider_connection_id
                ),
                status=payload.status,
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
    return ProviderConnectionResponseSchema(
        provider_connection_id=result.provider_connection_id,
        tenant_id=result.tenant_id,
        provider_connector_id=result.provider_connector_id,
        connection_code=result.connection_code,
        connection_name=result.connection_name,
        channel_code=result.channel_code,
        config=result.config,
        secret_ref=result.secret_ref,
        has_secrets=result.has_secrets,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


__all__ = [
    "UpdateProviderConnectionStatusRequestSchema",
    "router",
    "update_provider_connection_status",
]
