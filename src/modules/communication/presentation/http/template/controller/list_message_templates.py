from fastapi import APIRouter, HTTPException, status

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    ListMessageTemplatesUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.template.responses import (
    ListMessageTemplatesResponseSchema,
    MessageTemplateResponseSchema,
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

router = APIRouter(prefix="/communication/templates", tags=["communication"])


@router.get("", response_model=ListMessageTemplatesResponseSchema)
async def list_message_templates(
    context: AuthenticatedRequestContextDep,
    use_case: ListMessageTemplatesUseCaseDep,
) -> ListMessageTemplatesResponseSchema:
    """HTTP endpoint списка message templates текущего tenant."""
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
    return ListMessageTemplatesResponseSchema(
        items=[MessageTemplateResponseSchema(**item.__dict__) for item in items]
    )


__all__ = [
    "list_message_templates",
    "router",
]
