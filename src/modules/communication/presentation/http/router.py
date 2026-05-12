from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.communication.application.dto import SendCommunicationResultDTO
from src.modules.communication.application.use_cases import (
    ActivateTemplateVersionCommand,
    CreateMessageTemplateCommand,
    CreateProviderConnectionCommand,
    CreateTemplateVersionCommand,
    HandleProviderWebhookCommand,
    RegisterProviderConnectorCommand,
    SendCommunicationCommand,
    utc_now,
)
from src.modules.communication.domain import (
    CommunicationError,
    CommunicationNotFoundError,
    CommunicationValidationError,
    OutboundMessageStatus,
)
from src.modules.communication.presentation.depends.application import (
    ActivateTemplateVersionUseCaseDep,
    CommunicationRepositoryDep,
    CreateMessageTemplateUseCaseDep,
    CreateProviderConnectionUseCaseDep,
    CreateTemplateVersionUseCaseDep,
    GetOutboundMessageUseCaseDep,
    HandleProviderWebhookUseCaseDep,
    ListMessageTemplatesUseCaseDep,
    ListOutboundMessagesUseCaseDep,
    ListProviderConnectionsUseCaseDep,
    ListProviderConnectorsUseCaseDep,
    OutboundMessagePublisherDep,
    RegisterProviderConnectorUseCaseDep,
    SendCommunicationUseCaseDep,
)
from src.modules.shared.depends import (
    AuthenticatedRequestContextDep,
    OptionalRequestContextDep,
    UoWDep,
)
from src.modules.shared.kernel.request_context import RequestContext

log = logging.getLogger(__name__)

router = APIRouter(prefix="/communication", tags=["communication"])


class ImportYamlRequestSchema(BaseModel):
    yaml_content: str


class ProviderConnectorResponseSchema(BaseModel):
    provider_connector_id: UUID
    provider_code: str
    provider_name: str
    version: str
    connector_type: str
    channels: list[str]
    config_schema: dict[str, Any]
    secrets_schema: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class ProviderMessageTypeResponseSchema(BaseModel):
    provider_message_type_id: UUID
    provider_connector_id: UUID
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


class ListProviderConnectorsResponseSchema(BaseModel):
    connectors: list[ProviderConnectorResponseSchema]
    message_types: list[ProviderMessageTypeResponseSchema]


class CreateProviderConnectionRequestSchema(BaseModel):
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)
    secret_ref: str | None = None


class ProviderConnectionResponseSchema(BaseModel):
    provider_connection_id: UUID
    tenant_id: UUID
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    has_secrets: bool
    status: str
    created_at: datetime
    updated_at: datetime


class ListProviderConnectionsResponseSchema(BaseModel):
    items: list[ProviderConnectionResponseSchema]


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


class SendCommunicationRequestSchema(BaseModel):
    initiator_type: str
    message_class: str
    channel_code: str
    recipient_address: str
    template_code: str | None = None
    template_id: UUID | None = None
    initiator_ref_id: str | None = None
    correlation_id: UUID | None = None
    idempotency_key: str | None = None
    contact_id: UUID | None = None
    recipient_snapshot: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


class SendCommunicationResponseSchema(BaseModel):
    communication_request_id: UUID
    outbound_message_id: UUID
    status: str
    internal_status: str
    idempotent: bool


class OutboundMessageResponseSchema(BaseModel):
    outbound_message_id: UUID
    tenant_id: UUID
    communication_request_id: UUID
    provider_connection_id: UUID
    channel_code: str
    contact_id: UUID | None
    recipient_address: str
    rendered_payload: dict[str, Any]
    provider_request_payload: dict[str, Any]
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    error_code: str | None
    error_message: str | None
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ListOutboundMessagesResponseSchema(BaseModel):
    items: list[OutboundMessageResponseSchema]


class WebhookResponseSchema(BaseModel):
    accepted: bool
    matched: bool
    outbound_message_id: UUID | None
    internal_status: str | None


@router.post(
    "/providers/connectors/import-yaml",
    response_model=ProviderConnectorResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def import_provider_connector_yaml(
    payload: ImportYamlRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: RegisterProviderConnectorUseCaseDep,
) -> ProviderConnectorResponseSchema:
    tenant_id = _require_tenant_id(context)
    try:
        result = await use_case(
            RegisterProviderConnectorCommand(
                tenant_id=tenant_id,
                yaml_content=payload.yaml_content,
            )
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return ProviderConnectorResponseSchema(**asdict(result))


@router.get(
    "/providers/connectors",
    response_model=ListProviderConnectorsResponseSchema,
)
async def list_provider_connectors(
    context: AuthenticatedRequestContextDep,
    use_case: ListProviderConnectorsUseCaseDep,
) -> ListProviderConnectorsResponseSchema:
    tenant_id = _require_tenant_id(context)
    connectors, message_types = await use_case(tenant_id)
    return ListProviderConnectorsResponseSchema(
        connectors=[
            ProviderConnectorResponseSchema(**asdict(item)) for item in connectors
        ],
        message_types=[
            ProviderMessageTypeResponseSchema(**asdict(item)) for item in message_types
        ],
    )


@router.post(
    "/providers/connections",
    response_model=ProviderConnectionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider_connection(
    payload: CreateProviderConnectionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateProviderConnectionUseCaseDep,
) -> ProviderConnectionResponseSchema:
    tenant_id = _require_tenant_id(context)
    try:
        result = await use_case(
            CreateProviderConnectionCommand(
                tenant_id=tenant_id,
                provider_connector_id=payload.provider_connector_id,
                connection_code=payload.connection_code,
                connection_name=payload.connection_name,
                channel_code=payload.channel_code,
                config=payload.config,
                secrets=payload.secrets,
                secret_ref=payload.secret_ref,
            )
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return ProviderConnectionResponseSchema(**asdict(result))


@router.get(
    "/providers/connections",
    response_model=ListProviderConnectionsResponseSchema,
)
async def list_provider_connections(
    context: AuthenticatedRequestContextDep,
    use_case: ListProviderConnectionsUseCaseDep,
) -> ListProviderConnectionsResponseSchema:
    tenant_id = _require_tenant_id(context)
    items = await use_case(tenant_id)
    return ListProviderConnectionsResponseSchema(
        items=[ProviderConnectionResponseSchema(**asdict(item)) for item in items]
    )


@router.post(
    "/templates",
    response_model=MessageTemplateResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_message_template(
    payload: CreateMessageTemplateRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateMessageTemplateUseCaseDep,
) -> MessageTemplateResponseSchema:
    tenant_id = _require_tenant_id(context)
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
    except CommunicationError as exc:
        _raise_http_error(exc)
    return MessageTemplateResponseSchema(**asdict(result))


@router.post(
    "/templates/{template_id}/versions",
    response_model=TemplateVersionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_template_version(
    template_id: UUID,
    payload: CreateTemplateVersionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateTemplateVersionUseCaseDep,
) -> TemplateVersionResponseSchema:
    tenant_id = _require_tenant_id(context)
    try:
        result = await use_case(
            CreateTemplateVersionCommand(
                tenant_id=tenant_id,
                template_id=template_id,
                template_payload=payload.template_payload,
                variables_schema=payload.variables_schema,
            )
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return TemplateVersionResponseSchema(**asdict(result))


@router.post(
    "/templates/{template_id}/versions/{version_id}/activate",
    response_model=TemplateVersionResponseSchema,
)
async def activate_template_version(
    template_id: UUID,
    version_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: ActivateTemplateVersionUseCaseDep,
) -> TemplateVersionResponseSchema:
    tenant_id = _require_tenant_id(context)
    try:
        result = await use_case(
            ActivateTemplateVersionCommand(
                tenant_id=tenant_id,
                template_id=template_id,
                template_version_id=version_id,
            )
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return TemplateVersionResponseSchema(**asdict(result))


@router.get("/templates", response_model=ListMessageTemplatesResponseSchema)
async def list_message_templates(
    context: AuthenticatedRequestContextDep,
    use_case: ListMessageTemplatesUseCaseDep,
) -> ListMessageTemplatesResponseSchema:
    tenant_id = _require_tenant_id(context)
    items = await use_case(tenant_id)
    return ListMessageTemplatesResponseSchema(
        items=[MessageTemplateResponseSchema(**asdict(item)) for item in items]
    )


@router.post(
    "/send",
    response_model=SendCommunicationResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_communication(
    payload: SendCommunicationRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: SendCommunicationUseCaseDep,
    uow: UoWDep,
    repository: CommunicationRepositoryDep,
    publisher: OutboundMessagePublisherDep,
) -> SendCommunicationResponseSchema:
    tenant_id = _require_tenant_id(context)
    try:
        result = await use_case(
            SendCommunicationCommand(
                tenant_id=tenant_id,
                initiator_type=payload.initiator_type,
                message_class=payload.message_class,
                channel_code=payload.channel_code,
                recipient_address=payload.recipient_address,
                template_code=payload.template_code,
                template_id=payload.template_id,
                initiator_ref_id=payload.initiator_ref_id,
                correlation_id=payload.correlation_id,
                idempotency_key=payload.idempotency_key,
                contact_id=payload.contact_id,
                recipient_snapshot=payload.recipient_snapshot,
                variables=payload.variables,
                scheduled_at=payload.scheduled_at,
                priority=payload.priority,
            )
        )
        await uow.commit()
        await _publish_send_job_after_commit(
            tenant_id=tenant_id,
            result=result,
            repository=repository,
            publisher=publisher,
            uow=uow,
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return SendCommunicationResponseSchema(**asdict(result))


@router.get("/messages", response_model=ListOutboundMessagesResponseSchema)
async def list_messages(
    context: AuthenticatedRequestContextDep,
    use_case: ListOutboundMessagesUseCaseDep,
    limit: int = 100,
    offset: int = 0,
) -> ListOutboundMessagesResponseSchema:
    tenant_id = _require_tenant_id(context)
    items = await use_case(tenant_id=tenant_id, limit=limit, offset=offset)
    return ListOutboundMessagesResponseSchema(
        items=[OutboundMessageResponseSchema(**asdict(item)) for item in items]
    )


@router.get(
    "/messages/{outbound_message_id}",
    response_model=OutboundMessageResponseSchema,
)
async def get_message(
    outbound_message_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: GetOutboundMessageUseCaseDep,
) -> OutboundMessageResponseSchema:
    tenant_id = _require_tenant_id(context)
    try:
        result = await use_case(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return OutboundMessageResponseSchema(**asdict(result))


@router.post(
    "/webhooks/{tenant_id}/{provider_code}",
    response_model=WebhookResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
)
async def handle_provider_webhook(
    tenant_id: UUID,
    provider_code: str,
    raw_payload: dict[str, Any],
    _context: OptionalRequestContextDep,
    use_case: HandleProviderWebhookUseCaseDep,
) -> WebhookResponseSchema:
    try:
        result = await use_case(
            HandleProviderWebhookCommand(
                tenant_id=tenant_id,
                provider_code=provider_code,
                raw_payload=raw_payload,
            )
        )
    except CommunicationError as exc:
        _raise_http_error(exc)
    return WebhookResponseSchema(**asdict(result))


def _require_tenant_id(context: RequestContext) -> UUID:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return principal.tenant_id


def _raise_http_error(exc: CommunicationError) -> None:
    if isinstance(exc, CommunicationNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, CommunicationValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    ) from exc


async def _publish_send_job_after_commit(
    *,
    tenant_id: UUID,
    result: SendCommunicationResultDTO,
    repository: CommunicationRepositoryDep,
    publisher: OutboundMessagePublisherDep,
    uow: UoWDep,
) -> None:
    if publisher is None:
        return
    if result.internal_status != OutboundMessageStatus.QUEUED.value:
        return

    published_at = utc_now()
    try:
        await publisher.publish(
            tenant_id=tenant_id,
            outbound_message_id=result.outbound_message_id,
            published_at=published_at,
            source="send_communication",
        )
        await repository.mark_outbound_published(
            tenant_id=tenant_id,
            outbound_message_id=result.outbound_message_id,
            published_at=published_at,
        )
        await uow.commit()
    except Exception:
        await uow.rollback()
        log.warning(
            "Failed to publish outbound communication message after send commit.",
            extra={"outbound_message_id": str(result.outbound_message_id)},
            exc_info=True,
        )


__all__ = ["router"]
