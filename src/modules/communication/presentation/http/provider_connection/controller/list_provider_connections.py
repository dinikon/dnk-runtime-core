from fastapi import APIRouter, HTTPException, status

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    ListProviderConnectionsUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.provider_connection.responses import (
    ListProviderConnectionsResponseSchema,
    ProviderConnectionResponseSchema,
)
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
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/communication/providers", tags=["communication"])


@router.get(
    "/connections",
    response_model=ListProviderConnectionsResponseSchema,
)
async def list_provider_connections(
    context: AuthenticatedRequestContextDep,
    use_case: ListProviderConnectionsUseCaseDep,
) -> ListProviderConnectionsResponseSchema:
    """HTTP endpoint списка provider connections текущего tenant."""
    tenant_id = EntityIdVO.from_value(require_tenant_id(context))
    try:
        items = await use_case(tenant_id)
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
    return ListProviderConnectionsResponseSchema(
        items=[
            ProviderConnectionResponseSchema(
                provider_connection_id=item.provider_connection_id,
                tenant_id=item.tenant_id,
                provider_connector_id=item.provider_connector_id,
                connection_code=item.connection_code,
                connection_name=item.connection_name,
                channel_code=item.channel_code,
                config=item.config,
                secret_ref=item.secret_ref,
                has_secrets=item.has_secrets,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


__all__ = [
    "list_provider_connections",
    "router",
]
