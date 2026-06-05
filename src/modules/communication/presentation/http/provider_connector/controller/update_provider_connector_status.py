from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.provider_connector import (
    UpdateProviderConnectorStatusCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.communication.presentation.depends.application import (
    UpdateProviderConnectorStatusUseCaseDep,
)
from src.modules.communication.presentation.http.provider_connector.requests import (
    UpdateProviderConnectorStatusRequestSchema,
)
from src.modules.communication.presentation.http.provider_connector.responses import (
    ProviderConnectorResponseSchema,
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

router = APIRouter(prefix="/communication/providers", tags=["communication"])


@router.patch(
    "/connectors/{provider_connector_id}/status",
    response_model=ProviderConnectorResponseSchema,
)
async def update_provider_connector_status(
    provider_connector_id: UUID,
    payload: UpdateProviderConnectorStatusRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateProviderConnectorStatusUseCaseDep,
) -> ProviderConnectorResponseSchema:
    """HTTP endpoint смены статуса provider connector текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await use_case(
            UpdateProviderConnectorStatusCommand(
                tenant_id=tenant_id,
                provider_connector_id=ProviderConnectorIdVO.from_value(
                    provider_connector_id
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
    return ProviderConnectorResponseSchema(
        provider_connector_id=result.provider_connector_id,
        provider_code=result.provider_code,
        provider_name=result.provider_name,
        version=result.version,
        connector_type=result.connector_type,
        channels=list(result.channels),
        config_schema=dict(result.config_schema),
        secrets_schema=dict(result.secrets_schema),
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


__all__ = [
    "UpdateProviderConnectorStatusRequestSchema",
    "router",
    "update_provider_connector_status",
]
