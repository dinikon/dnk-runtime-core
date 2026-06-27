import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.provider_connection import (
    CreateProviderConnectionCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.communication.presentation.depends.application import (
    CreateProviderConnectionUseCaseDep,
)
from src.modules.communication.presentation.http.provider_connection.requests import (
    CreateProviderConnectionRequestSchema,
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
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared import DomainError

router = APIRouter(prefix="/communication/providers", tags=["communication"])


@router.post(
    "/connections",
    response_model=ProviderConnectionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider_connection(
    payload: CreateProviderConnectionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateProviderConnectionUseCaseDep,
) -> ProviderConnectionResponseSchema:
    """HTTP endpoint создания provider connection текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await use_case(
            CreateProviderConnectionCommand(
                tenant_id=tenant_id,
                provider_connection_id=ProviderConnectionIdVO.from_value(uuid6.uuid7()),
                provider_connector_id=ProviderConnectorIdVO.from_value(
                    payload.provider_connector_id
                ),
                connection_name=payload.connection_name,
                channel_code=payload.channel_code,
                config=payload.config,
                secrets=payload.secrets,
                secret_ref=payload.secret_ref,
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
    "CreateProviderConnectionRequestSchema",
    "create_provider_connection",
    "router",
]
