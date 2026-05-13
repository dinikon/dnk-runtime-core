from fastapi import APIRouter, HTTPException, status

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    ListProviderConnectorsUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.provider_connector.responses import (
    ListProviderConnectorsResponseSchema,
    ProviderConnectorResponseSchema,
    ProviderMessageTypeResponseSchema,
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
    "/connectors",
    response_model=ListProviderConnectorsResponseSchema,
)
async def list_provider_connectors(
    context: AuthenticatedRequestContextDep,
    use_case: ListProviderConnectorsUseCaseDep,
) -> ListProviderConnectorsResponseSchema:
    """HTTP endpoint списка provider connectors текущего tenant."""
    tenant_id = EntityIdVO.from_value(require_tenant_id(context))
    try:
        result = await use_case(tenant_id)
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
    return ListProviderConnectorsResponseSchema(
        connectors=[
            ProviderConnectorResponseSchema(
                provider_connector_id=item.provider_connector_id,
                provider_code=item.provider_code,
                provider_name=item.provider_name,
                version=item.version,
                connector_type=item.connector_type,
                channels=list(item.channels),
                config_schema=dict(item.config_schema),
                secrets_schema=dict(item.secrets_schema),
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result.connectors
        ],
        message_types=[
            ProviderMessageTypeResponseSchema(
                provider_message_type_id=item.provider_message_type_id,
                provider_connector_id=item.provider_connector_id,
                message_type_code=item.message_type_code,
                channel_code=item.channel_code,
                name=item.name,
                field_schema=dict(item.field_schema),
                ui_schema=dict(item.ui_schema),
                is_active=item.is_active,
            )
            for item in result.message_types
        ],
    )


__all__ = ["list_provider_connectors", "router"]
