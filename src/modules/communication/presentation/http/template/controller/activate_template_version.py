from fastapi import APIRouter, HTTPException, status
from uuid import UUID

from src.modules.communication.application.template import (
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
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.template.responses import (
    TemplateVersionResponseSchema,
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
    tenant_id = EntityIdVO.from_value(require_tenant_id(context))
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
    return TemplateVersionResponseSchema(**result.__dict__)


__all__ = [
    "activate_template_version",
    "router",
]
