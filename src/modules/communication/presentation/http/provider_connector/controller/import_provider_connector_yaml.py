import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.provider_connector import (
    RegisterProviderConnectorCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.communication.presentation.depends.application import (
    RegisterProviderConnectorUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.provider_connector.requests import (
    ImportYamlRequestSchema,
)
from src.modules.communication.presentation.http.provider_connector.responses import (
    ProviderConnectorResponseSchema,
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


@router.post(
    "/connectors/import-yaml",
    response_model=ProviderConnectorResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def import_provider_connector_yaml(
    payload: ImportYamlRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: RegisterProviderConnectorUseCaseDep,
) -> ProviderConnectorResponseSchema:
    """HTTP endpoint импорта provider connector YAML текущего tenant."""
    tenant_id = EntityIdVO.from_value(require_tenant_id(context))
    try:
        result = await use_case(
            RegisterProviderConnectorCommand(
                tenant_id=tenant_id,
                provider_connector_id=ProviderConnectorIdVO.from_value(uuid6.uuid7()),
                yaml_content=payload.yaml_content,
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
    "ImportYamlRequestSchema",
    "import_provider_connector_yaml",
    "router",
]
