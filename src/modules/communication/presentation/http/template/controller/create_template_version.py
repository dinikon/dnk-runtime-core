import uuid6
from fastapi import APIRouter, HTTPException, status
from uuid import UUID

from src.modules.communication.application.template import CreateTemplateVersionCommand
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
    CreateTemplateVersionUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.communication.presentation.http.template.requests import (
    CreateTemplateVersionRequestSchema,
)
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
    "/{template_id}/versions",
    response_model=TemplateVersionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_template_version(
    template_id: UUID,
    payload: CreateTemplateVersionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateTemplateVersionUseCaseDep,
) -> TemplateVersionResponseSchema:
    """HTTP endpoint создания версии message template."""
    tenant_id = EntityIdVO.from_value(require_tenant_id(context))
    try:
        result = await use_case(
            CreateTemplateVersionCommand(
                tenant_id=tenant_id,
                template_id=MessageTemplateIdVO.from_value(template_id),
                template_version_id=TemplateVersionIdVO.from_value(uuid6.uuid7()),
                template_payload=payload.template_payload,
                variables_schema=payload.variables_schema,
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
    "CreateTemplateVersionRequestSchema",
    "create_template_version",
    "router",
]
