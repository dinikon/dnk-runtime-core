import uuid6
from fastapi import APIRouter, HTTPException, status

from src.modules.communication.application.message_template import (
    CreateMessageTemplateCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.domain.message_template import MessageTemplateIdVO
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)
from src.modules.communication.presentation.depends.application import (
    CreateMessageTemplateUseCaseDep,
)
from src.modules.communication.presentation.http.message_template.requests import (
    CreateMessageTemplateRequestSchema,
)
from src.modules.communication.presentation.http.message_template.responses import (
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
from src.modules.shared import DomainError

router = APIRouter(prefix="/communication/templates", tags=["communication"])


@router.post(
    "",
    response_model=MessageTemplateResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_message_template(
    payload: CreateMessageTemplateRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateMessageTemplateUseCaseDep,
) -> MessageTemplateResponseSchema:
    """HTTP endpoint создания message template текущего tenant."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    tenant_id = EntityIdVO.from_value(principal.tenant_id)
    try:
        result = await use_case(
            CreateMessageTemplateCommand(
                tenant_id=tenant_id,
                template_id=MessageTemplateIdVO.from_value(uuid6.uuid7()),
                template_code=payload.template_code,
                name=payload.name,
                description=payload.description,
                provider_connector_id=ProviderConnectorIdVO.from_value(
                    payload.provider_connector_id
                ),
                provider_message_type_id=ProviderMessageTypeIdVO.from_value(
                    payload.provider_message_type_id
                ),
                channel_code=payload.channel_code,
                message_class=payload.message_class,
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
    return MessageTemplateResponseSchema(
        template_id=result.template_id,
        tenant_id=result.tenant_id,
        template_code=result.template_code,
        name=result.name,
        description=result.description,
        provider_connector_id=result.provider_connector_id,
        provider_message_type_id=result.provider_message_type_id,
        channel_code=result.channel_code,
        message_class=result.message_class,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
        active_version_id=result.active_version_id,
        active_version=result.active_version,
    )


__all__ = [
    "CreateMessageTemplateRequestSchema",
    "create_message_template",
    "router",
]
