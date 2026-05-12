from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.communication.application.template import (
    ActivateTemplateVersionCommand,
    CreateMessageTemplateCommand,
    CreateTemplateVersionCommand,
)
from src.modules.communication.domain import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    ActivateTemplateVersionUseCaseDep,
    CreateMessageTemplateUseCaseDep,
    CreateTemplateVersionUseCaseDep,
    ListMessageTemplatesUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
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
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/communication/templates", tags=["communication"])


class CreateMessageTemplateRequestSchema(BaseModel):
    template_code: str
    name: str
    description: str | None = None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    message_class: str


class MessageTemplateResponseSchema(BaseModel):
    template_id: UUID
    tenant_id: UUID
    template_code: str
    name: str
    description: str | None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    message_class: str
    status: str
    created_at: datetime
    updated_at: datetime
    active_version_id: UUID | None = None
    active_version_no: int | None = None


class CreateTemplateVersionRequestSchema(BaseModel):
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any] = Field(default_factory=dict)


class TemplateVersionResponseSchema(BaseModel):
    template_version_id: UUID
    template_id: UUID
    version_no: int
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any]
    status: str
    created_at: datetime
    activated_at: datetime | None


class ListMessageTemplatesResponseSchema(BaseModel):
    items: list[MessageTemplateResponseSchema]


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
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            CreateMessageTemplateCommand(
                tenant_id=tenant_id,
                template_code=payload.template_code,
                name=payload.name,
                description=payload.description,
                provider_connector_id=payload.provider_connector_id,
                provider_message_type_id=payload.provider_message_type_id,
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
        active_version_no=result.active_version_no,
    )


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
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            CreateTemplateVersionCommand(
                tenant_id=tenant_id,
                template_id=template_id,
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
    return TemplateVersionResponseSchema(
        template_version_id=result.template_version_id,
        template_id=result.template_id,
        version_no=result.version_no,
        template_payload=dict(result.template_payload),
        variables_schema=dict(result.variables_schema),
        status=result.status,
        created_at=result.created_at,
        activated_at=result.activated_at,
    )


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
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            ActivateTemplateVersionCommand(
                tenant_id=tenant_id,
                template_id=template_id,
                template_version_id=version_id,
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
        version_no=result.version_no,
        template_payload=dict(result.template_payload),
        variables_schema=dict(result.variables_schema),
        status=result.status,
        created_at=result.created_at,
        activated_at=result.activated_at,
    )


@router.get("", response_model=ListMessageTemplatesResponseSchema)
async def list_message_templates(
    context: AuthenticatedRequestContextDep,
    use_case: ListMessageTemplatesUseCaseDep,
) -> ListMessageTemplatesResponseSchema:
    tenant_id = require_tenant_id(context)
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
                active_version_no=item.active_version_no,
            )
            for item in items
        ]
    )


__all__ = [
    "CreateMessageTemplateRequestSchema",
    "CreateTemplateVersionRequestSchema",
    "ListMessageTemplatesResponseSchema",
    "MessageTemplateResponseSchema",
    "TemplateVersionResponseSchema",
    "router",
]
