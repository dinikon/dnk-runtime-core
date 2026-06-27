from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.communication.application.provider_connector import (
    DeleteProviderConnectorCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.communication.presentation.depends.application import (
    DeleteProviderConnectorUseCaseDep,
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


@router.delete(
    "/connectors/{provider_connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_provider_connector(
    provider_connector_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteProviderConnectorUseCaseDep,
) -> Response:
    """HTTP endpoint удаления provider connector текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        await use_case(
            DeleteProviderConnectorCommand(
                tenant_id=tenant_id,
                provider_connector_id=ProviderConnectorIdVO.from_value(
                    provider_connector_id
                ),
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["delete_provider_connector", "router"]
