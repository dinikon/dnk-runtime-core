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
from src.modules.communication.presentation.http.message_template.responses import (
    ListMessageTemplatesResponseSchema,
    MessageTemplateResponseSchema,
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
        items=[
            MessageTemplateResponseSchema(
                template_id=item.template_id,
                tenant_id=item.tenant_id,
                template_code=item.template_code,
                name=item.name,
                description=item.description,
                provider_connector_id=item.provider_connector_id,
                provider_message_type_id=item.provider_message_type_id,
                channel_code=item.channel_code,
                message_class=item.message_class,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
                active_version_id=item.active_version_id,
                active_version=item.active_version,
            )
            for item in items
        ]
    )


__all__ = [
    "list_message_templates",
    "router",
]
