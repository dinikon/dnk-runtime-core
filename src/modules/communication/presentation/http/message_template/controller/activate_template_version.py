from fastapi import APIRouter, HTTPException, status
from uuid import UUID

from src.modules.communication.application.message_template import (
    ActivateTemplateVersionCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.presentation.depends.application import (
    ActivateTemplateVersionUseCaseDep,
)
from src.modules.communication.presentation.http.message_template.responses import (
    TemplateVersionResponseSchema,
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


@router.post(
    "/{template_id}/versions/{version_id}/activate",
    response_model=TemplateVersionResponseSchema,
)
async def activate_template_version(
    template_id: UUID,
    version_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ActivateTemplateVersionUseCaseDep,
) -> TemplateVersionResponseSchema:
    """HTTP endpoint активации версии message template."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await use_case(
            ActivateTemplateVersionCommand(
                tenant_id=tenant_id,
                template_id=MessageTemplateIdVO.from_value(template_id),
                template_version_id=TemplateVersionIdVO.from_value(version_id),
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
    return TemplateVersionResponseSchema(
        template_version_id=result.template_version_id,
        template_id=result.template_id,
        version=result.version,
        template_payload=dict(result.template_payload),
        variables_schema=dict(result.variables_schema),
        status=result.status,
        created_at=result.created_at,
        activated_at=result.activated_at,
    )


__all__ = [
    "activate_template_version",
    "router",
]
