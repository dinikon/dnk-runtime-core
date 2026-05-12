from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.communication.application.dto import (
    MessageTemplateDTO,
    OutboundMessageDTO,
    ProcessOutboundMessageResultDTO,
    ProcessQueuedResultDTO,
    ProviderConnectionDTO,
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
    PublishQueuedResultDTO,
    RecoverStuckResultDTO,
    SendCommunicationResultDTO,
    TemplateVersionDTO,
    WebhookResultDTO,
)
from src.modules.communication.application.ports import (
    OutboundMessagePublisherProtocol,
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderRegistryProtocol,
)
from src.modules.communication.application.services import (
    JsonSchemaValidationService,
    ProviderStatusMappingService,
    ProviderYamlLoader,
    TemplateRenderService,
)
from src.modules.communication.domain import (
    CommunicationNotFoundError,
    CommunicationValidationError,
    DeliveryEventType,
    OutboundMessageStatus,
    TemplateVersionStatus,
)
from src.modules.communication.infrastructure.repository import (
    CommunicationRepository,
    connection_to_dto,
    connector_to_dto,
    message_type_to_dto,
    outbound_to_dto,
    template_to_dto,
    template_version_to_dto,
    utc_now,
)
from src.modules.shared.db.uow import UnitOfWork


@dataclass(frozen=True, slots=True)
class RegisterProviderConnectorCommand:
    tenant_id: UUID
    yaml_content: str


@dataclass(frozen=True, slots=True)
class CreateProviderConnectionCommand:
    tenant_id: UUID
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, Any] = field(default_factory=dict)
    secret_ref: str | None = None


@dataclass(frozen=True, slots=True)
class CreateMessageTemplateCommand:
    tenant_id: UUID
    template_code: str
    name: str
    description: str | None
    provider_connector_id: UUID
    provider_message_type_id: UUID
    channel_code: str
    message_class: str


@dataclass(frozen=True, slots=True)
class CreateTemplateVersionCommand:
    tenant_id: UUID
    template_id: UUID
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ActivateTemplateVersionCommand:
    tenant_id: UUID
    template_id: UUID
    template_version_id: UUID


@dataclass(frozen=True, slots=True)
class SendCommunicationCommand:
    tenant_id: UUID
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
    recipient_snapshot: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


@dataclass(frozen=True, slots=True)
class ProcessQueuedMessagesCommand:
    tenant_id: UUID
    limit: int = 100


@dataclass(frozen=True, slots=True)
class ProcessOutboundMessageByIdCommand:
    tenant_id: UUID
    outbound_message_id: UUID


@dataclass(frozen=True, slots=True)
class PublishQueuedOutboundMessagesCommand:
    tenant_id: UUID
    limit: int = 100
    source: str = "republisher"


@dataclass(frozen=True, slots=True)
class RecoverStuckOutboundMessagesCommand:
    tenant_id: UUID
    older_than_seconds: int = 300
    limit: int = 100


@dataclass(frozen=True, slots=True)
class HandleProviderWebhookCommand:
    tenant_id: UUID
    provider_code: str
    raw_payload: dict[str, Any]


class RegisterProviderConnectorUseCase:
    """Imports provider YAML and extracts provider message types."""

    def __init__(
        self,
        repository: CommunicationRepository,
        loader: ProviderYamlLoader,
    ) -> None:
        self._repository = repository
        self._loader = loader

    async def __call__(
        self,
        command: RegisterProviderConnectorCommand,
    ) -> ProviderConnectorDTO:
        parsed = self._loader.load(command.yaml_content)
        spec = parsed.spec
        connector = await self._repository.upsert_connector(
            tenant_id=command.tenant_id,
            provider_code=str(spec["provider_code"]),
            provider_name=str(spec["provider_name"]),
            version=str(spec["version"]),
            connector_type=str(spec["connector_type"]),
            yaml_spec=spec,
            yaml_checksum=parsed.checksum,
        )
        for message_type in spec["message_types"]:
            await self._repository.upsert_message_type(
                tenant_id=command.tenant_id,
                provider_connector_id=connector.provider_connector_id,
                message_type_code=str(message_type["code"]),
                channel_code=str(message_type["channel"]),
                name=str(message_type["name"]),
                field_schema=dict(message_type["field_schema"]),
                ui_schema=dict(message_type.get("ui_schema") or {}),
            )
        return connector_to_dto(connector)


class ListProviderConnectorsUseCase:
    """Lists provider connectors and message types."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        tenant_id: UUID,
    ) -> tuple[list[ProviderConnectorDTO], list[ProviderMessageTypeDTO]]:
        connectors = [
            connector_to_dto(item)
            for item in await self._repository.list_connectors(tenant_id)
        ]
        message_types = [
            message_type_to_dto(item)
            for item in await self._repository.list_message_types(tenant_id)
        ]
        return connectors, message_types


class CreateProviderConnectionUseCase:
    """Creates tenant provider connections with write-only base64 secrets."""

    def __init__(
        self,
        repository: CommunicationRepository,
        schema_validator: JsonSchemaValidationService,
        secret_codec: SecretCodec,
    ) -> None:
        self._repository = repository
        self._schema_validator = schema_validator
        self._secret_codec = secret_codec

    async def __call__(
        self,
        command: CreateProviderConnectionCommand,
    ) -> ProviderConnectionDTO:
        connector = await self._repository.get_connector(
            command.tenant_id,
            command.provider_connector_id,
        )
        if connector is None:
            raise CommunicationNotFoundError("Provider connector was not found.")
        spec = connector.yaml_spec
        if command.channel_code not in set(spec.get("channels") or []):
            raise CommunicationValidationError(
                "Provider connector does not support requested channel."
            )
        self._schema_validator.validate(
            command.config, spec.get("config_schema"), "config"
        )
        self._schema_validator.validate(
            command.secrets,
            spec.get("secrets_schema"),
            "secrets",
        )
        connection = await self._repository.create_connection(
            tenant_id=command.tenant_id,
            provider_connector_id=command.provider_connector_id,
            connection_code=command.connection_code,
            connection_name=command.connection_name,
            channel_code=command.channel_code,
            config=command.config,
            secret_ref=command.secret_ref,
            secrets_b64=self._secret_codec.encode(command.secrets),
        )
        return connection_to_dto(connection)


class ListProviderConnectionsUseCase:
    """Lists tenant provider connections without exposing secrets."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(self, tenant_id: UUID) -> list[ProviderConnectionDTO]:
        return [
            connection_to_dto(item)
            for item in await self._repository.list_connections(tenant_id)
        ]


class CreateMessageTemplateUseCase:
    """Creates provider-bound message templates."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        command: CreateMessageTemplateCommand,
    ) -> MessageTemplateDTO:
        connector = await self._repository.get_connector(
            command.tenant_id,
            command.provider_connector_id,
        )
        if connector is None:
            raise CommunicationNotFoundError("Provider connector was not found.")
        message_type = await self._repository.get_message_type(
            command.tenant_id, command.provider_message_type_id
        )
        if message_type is None:
            raise CommunicationNotFoundError("Provider message type was not found.")
        if message_type.provider_connector_id != command.provider_connector_id:
            raise CommunicationValidationError(
                "Provider message type does not belong to provider connector."
            )
        if message_type.channel_code != command.channel_code:
            raise CommunicationValidationError(
                "Template channel must match provider message type channel."
            )
        template = await self._repository.create_template(
            tenant_id=command.tenant_id,
            template_code=command.template_code,
            name=command.name,
            description=command.description,
            provider_connector_id=command.provider_connector_id,
            provider_message_type_id=command.provider_message_type_id,
            channel_code=command.channel_code,
            message_class=command.message_class,
        )
        return template_to_dto(template)


class CreateTemplateVersionUseCase:
    """Creates a new validated template version."""

    def __init__(
        self,
        repository: CommunicationRepository,
        schema_validator: JsonSchemaValidationService,
    ) -> None:
        self._repository = repository
        self._schema_validator = schema_validator

    async def __call__(
        self,
        command: CreateTemplateVersionCommand,
    ) -> TemplateVersionDTO:
        template = await self._repository.get_template(
            tenant_id=command.tenant_id,
            template_id=command.template_id,
        )
        if template is None:
            raise CommunicationNotFoundError("Message template was not found.")
        message_type = await self._repository.get_message_type(
            command.tenant_id, template.provider_message_type_id
        )
        if message_type is None:
            raise CommunicationNotFoundError("Provider message type was not found.")
        self._schema_validator.validate(
            command.template_payload,
            message_type.field_schema,
            "template_payload",
        )
        self._schema_validator.check_schema(
            command.variables_schema, "variables_schema"
        )
        version = await self._repository.create_template_version(
            tenant_id=command.tenant_id,
            template_id=template.template_id,
            template_payload=command.template_payload,
            variables_schema=command.variables_schema,
        )
        return template_version_to_dto(version)


class ActivateTemplateVersionUseCase:
    """Activates a template version and deprecates the previous active version."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        command: ActivateTemplateVersionCommand,
    ) -> TemplateVersionDTO:
        template = await self._repository.get_template(
            tenant_id=command.tenant_id,
            template_id=command.template_id,
        )
        if template is None:
            raise CommunicationNotFoundError("Message template was not found.")
        version = await self._repository.get_template_version(
            command.tenant_id, command.template_version_id
        )
        if version is None or version.template_id != template.template_id:
            raise CommunicationNotFoundError("Template version was not found.")
        activated = await self._repository.activate_template_version(
            tenant_id=command.tenant_id,
            template=template,
            version=version,
            now=utc_now(),
        )
        return template_version_to_dto(activated)


class ListMessageTemplatesUseCase:
    """Lists tenant templates with active version metadata."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(self, tenant_id: UUID) -> list[MessageTemplateDTO]:
        templates = await self._repository.list_templates(tenant_id)
        result: list[MessageTemplateDTO] = []
        for template in templates:
            active_version = await self._repository.get_active_template_version(
                tenant_id, template.template_id
            )
            result.append(template_to_dto(template, active_version))
        return result


class SendCommunicationUseCase:
    """Accepts a send request and creates an outbound message for the worker."""

    def __init__(
        self,
        repository: CommunicationRepository,
        schema_validator: JsonSchemaValidationService,
    ) -> None:
        self._repository = repository
        self._schema_validator = schema_validator

    async def __call__(
        self,
        command: SendCommunicationCommand,
    ) -> SendCommunicationResultDTO:
        if command.template_id is None and command.template_code is None:
            raise CommunicationValidationError(
                "Either template_id or template_code is required."
            )
        if command.idempotency_key:
            existing = await self._repository.get_existing_send_by_idempotency(
                tenant_id=command.tenant_id,
                idempotency_key=command.idempotency_key,
            )
            if existing is not None:
                request, outbound = existing
                return SendCommunicationResultDTO(
                    communication_request_id=request.communication_request_id,
                    outbound_message_id=outbound.outbound_message_id,
                    status=request.status,
                    internal_status=outbound.internal_status,
                    idempotent=True,
                )

        if command.template_id is not None:
            template = await self._repository.get_template(
                tenant_id=command.tenant_id,
                template_id=command.template_id,
            )
        else:
            assert command.template_code is not None
            template = await self._repository.get_template_by_code(
                tenant_id=command.tenant_id,
                template_code=command.template_code,
            )
        if template is None:
            raise CommunicationNotFoundError("Message template was not found.")
        if template.channel_code != command.channel_code:
            raise CommunicationValidationError(
                "Send channel must match template channel."
            )
        active_version = await self._repository.get_active_template_version(
            command.tenant_id, template.template_id
        )
        if active_version is None:
            raise CommunicationValidationError(
                "Message template does not have an active version."
            )
        self._schema_validator.validate(
            command.variables,
            active_version.variables_schema,
            "variables",
        )
        connection = await self._repository.find_active_connection(
            tenant_id=command.tenant_id,
            provider_connector_id=template.provider_connector_id,
            channel_code=template.channel_code,
        )
        if connection is None:
            raise CommunicationValidationError(
                "No active provider connection found for template channel."
            )
        request, outbound = await self._repository.create_send_request(
            tenant_id=command.tenant_id,
            initiator_type=command.initiator_type,
            initiator_ref_id=command.initiator_ref_id,
            correlation_id=command.correlation_id,
            idempotency_key=command.idempotency_key,
            message_class=command.message_class,
            channel_code=command.channel_code,
            template_id=template.template_id,
            template_version_id=active_version.template_version_id,
            contact_id=command.contact_id,
            recipient_address=command.recipient_address,
            recipient_snapshot=command.recipient_snapshot,
            variables=command.variables,
            scheduled_at=command.scheduled_at,
            priority=command.priority,
            provider_connection_id=connection.provider_connection_id,
            now=utc_now(),
        )
        return SendCommunicationResultDTO(
            communication_request_id=request.communication_request_id,
            outbound_message_id=outbound.outbound_message_id,
            status=request.status,
            internal_status=outbound.internal_status,
            idempotent=False,
        )


class ProcessOutboundMessageUseCase:
    """Processes queued outbound messages through provider sender transports."""

    def __init__(
        self,
        repository: CommunicationRepository,
        sender_registry: ProviderSenderRegistryProtocol,
        template_renderer: TemplateRenderService,
    ) -> None:
        self._repository = repository
        self._sender_registry = sender_registry
        self._template_renderer = template_renderer

    async def __call__(
        self,
        command: ProcessQueuedMessagesCommand,
    ) -> ProcessQueuedResultDTO:
        queued = await self._repository.claim_queued_messages(
            command.tenant_id,
            command.limit,
        )
        succeeded = 0
        failed = 0
        for message in queued:
            try:
                await self._process_one(command.tenant_id, message.outbound_message_id)
                succeeded += 1
            except Exception:
                failed += 1
        return ProcessQueuedResultDTO(
            processed=len(queued),
            succeeded=succeeded,
            failed=failed,
        )

    async def _process_one(self, tenant_id: UUID, outbound_message_id: UUID) -> None:
        (
            outbound,
            request,
            _template,
            version,
            connection,
            connector,
            message_type,
        ) = await self._repository.load_processing_context(
            tenant_id, outbound_message_id
        )
        now = utc_now()
        attempt = None

        try:
            rendered_payload = self._template_renderer.render(
                version.template_payload,
                request.variables,
            )
            if not isinstance(rendered_payload, dict):
                raise CommunicationValidationError(
                    "Rendered template payload must be an object."
                )
            context = self._build_render_context(
                outbound=outbound,
                request=request,
                connection=connection,
                connector_spec=connector.yaml_spec,
                send_spec=self._resolve_send_spec(
                    connector.yaml_spec,
                    str(message_type.message_type_code),
                ),
                provider_message_type_code=str(message_type.message_type_code),
                rendered_payload=rendered_payload,
            )
            send_spec = context.send_spec
            sender = self._sender_registry.get(str(send_spec["transport"]))
            prepared = sender.build(context)
            attempt = await self._repository.create_delivery_attempt(
                tenant_id=tenant_id,
                outbound_message_id=outbound.outbound_message_id,
                provider_connection_id=connection.provider_connection_id,
                request_payload=prepared.request_payload,
            )
            response = await sender.send(context, prepared)
            if response.success:
                await self._repository.complete_outbound_processing(
                    tenant_id=tenant_id,
                    outbound_message_id=outbound.outbound_message_id,
                    processing_token=outbound.processing_token,
                    delivery_attempt_id=attempt.delivery_attempt_id,
                    rendered_payload=rendered_payload,
                    provider_request_payload=prepared.request_payload,
                    response_payload=response.response_payload,
                    http_status_code=response.http_status_code,
                    external_message_id=response.external_message_id,
                    external_status=response.external_status,
                    internal_status=response.internal_status,
                    finished_at=now,
                )
            else:
                await self._repository.fail_outbound_processing(
                    tenant_id=tenant_id,
                    outbound_message_id=outbound.outbound_message_id,
                    processing_token=outbound.processing_token,
                    delivery_attempt_id=attempt.delivery_attempt_id,
                    error_code=response.error_code or "PROVIDER_FAILED",
                    error_message=response.error_message or "Provider send failed.",
                    finished_at=now,
                    response_payload=response.response_payload,
                    http_status_code=response.http_status_code,
                    external_message_id=response.external_message_id,
                    external_status=response.external_status,
                )
        except Exception as exc:
            await self._repository.fail_outbound_processing(
                tenant_id=tenant_id,
                outbound_message_id=outbound.outbound_message_id,
                processing_token=outbound.processing_token,
                delivery_attempt_id=(
                    attempt.delivery_attempt_id if attempt is not None else None
                ),
                error_code=exc.__class__.__name__,
                error_message=str(exc),
                finished_at=now,
            )
            raise

    def _build_render_context(
        self,
        *,
        outbound,
        request,
        connection,
        connector_spec: dict[str, Any],
        send_spec: dict[str, Any],
        provider_message_type_code: str,
        rendered_payload: dict[str, Any],
    ) -> ProviderSendContext:
        return ProviderSendContext(
            outbound_message_id=outbound.outbound_message_id,
            communication_request_id=request.communication_request_id,
            initiator_ref_id=request.initiator_ref_id,
            recipient_address=outbound.recipient_address,
            recipient_snapshot=request.recipient_snapshot,
            variables=request.variables,
            connection_code=connection.connection_code,
            channel_code=connection.channel_code,
            provider_message_type_code=provider_message_type_code,
            config=connection.config,
            secrets_b64=connection.secrets_b64,
            connector_spec=connector_spec,
            send_spec=send_spec,
            rendered_payload=rendered_payload,
        )

    @staticmethod
    def _resolve_send_spec(
        connector_spec: dict[str, Any],
        message_type_code: str,
    ) -> dict[str, Any]:
        for message_type in connector_spec.get("message_types") or []:
            if not isinstance(message_type, dict):
                continue
            if str(message_type.get("code")) != message_type_code:
                continue
            send_spec = message_type.get("send")
            if send_spec is None:
                raise CommunicationValidationError(
                    f"Send spec is missing for provider message type '{message_type_code}'."
                )
            if not isinstance(send_spec, dict):
                raise CommunicationValidationError(
                    f"message type '{message_type_code}' send spec must be an object."
                )
            return send_spec

        raise CommunicationValidationError(
            f"No send spec found for provider message type '{message_type_code}'."
        )

    @staticmethod
    def _apply_status_timestamps(outbound, internal_status: str, now: datetime) -> None:
        if internal_status == OutboundMessageStatus.SENT.value:
            outbound.sent_at = outbound.sent_at or now
        elif internal_status == OutboundMessageStatus.DELIVERED.value:
            outbound.sent_at = outbound.sent_at or now
            outbound.delivered_at = outbound.delivered_at or now
        elif internal_status in (
            OutboundMessageStatus.FAILED.value,
            OutboundMessageStatus.EXPIRED.value,
            OutboundMessageStatus.UNDELIVERED.value,
        ):
            outbound.failed_at = outbound.failed_at or now


class ProcessOutboundMessageByIdUseCase:
    """Processes one outbound message with short DB transactions and a lease."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repository_factory: Callable[[AsyncSession], CommunicationRepository],
        sender_registry: ProviderSenderRegistryProtocol,
        template_renderer: TemplateRenderService,
        processing_lease_seconds: int,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._sender_registry = sender_registry
        self._template_renderer = template_renderer
        self._processing_lease_seconds = processing_lease_seconds

    async def __call__(
        self,
        command: ProcessOutboundMessageByIdCommand,
    ) -> ProcessOutboundMessageResultDTO:
        token = uuid4()
        now = utc_now()
        lease_until = now + timedelta(seconds=self._processing_lease_seconds)

        try:
            claimed = await self._claim_and_build(
                tenant_id=command.tenant_id,
                outbound_message_id=command.outbound_message_id,
                processing_token=token,
                now=now,
                lease_until=lease_until,
            )
        except _ProcessingSkipped as skipped:
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=command.outbound_message_id,
                processed=False,
                succeeded=False,
                skipped=True,
                status=skipped.status,
                error_message=skipped.reason,
            )
        if isinstance(claimed, _BuildFailed):
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=command.outbound_message_id,
                processed=True,
                succeeded=False,
                skipped=False,
                status=OutboundMessageStatus.FAILED.value,
                error_message=str(claimed.error),
            )

        prepared = claimed.prepared
        send_context = claimed.context
        attempt_id = claimed.delivery_attempt_id
        attempt_no = claimed.attempt_no
        sender = self._sender_registry.get(str(send_context.send_spec["transport"]))
        try:
            response = await sender.send(send_context, prepared)
        except Exception as exc:
            await self._persist_send_exception(
                outbound_message_id=command.outbound_message_id,
                tenant_id=command.tenant_id,
                processing_token=token,
                delivery_attempt_id=attempt_id,
                error=exc,
            )
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=command.outbound_message_id,
                processed=True,
                succeeded=False,
                skipped=False,
                status=OutboundMessageStatus.FAILED.value,
                error_message=str(exc),
            )

        if response.success:
            applied = await self._persist_success(
                outbound_message_id=command.outbound_message_id,
                tenant_id=command.tenant_id,
                processing_token=token,
                delivery_attempt_id=attempt_id,
                rendered_payload=send_context.rendered_payload,
                prepared=prepared,
                response=response,
            )
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=command.outbound_message_id,
                processed=applied,
                succeeded=applied,
                skipped=not applied,
                status=(
                    response.internal_status if applied else "STALE_PROCESSING_TOKEN"
                ),
            )

        retry_at = self._retry_at(
            connector_spec=send_context.connector_spec,
            attempt_no=attempt_no,
            response=response,
        )
        applied = await self._persist_provider_failure(
            outbound_message_id=command.outbound_message_id,
            tenant_id=command.tenant_id,
            processing_token=token,
            delivery_attempt_id=attempt_id,
            response=response,
            retry_at=retry_at,
        )
        return ProcessOutboundMessageResultDTO(
            outbound_message_id=command.outbound_message_id,
            processed=applied,
            succeeded=False,
            skipped=not applied,
            status=(
                OutboundMessageStatus.QUEUED.value
                if retry_at is not None and applied
                else OutboundMessageStatus.FAILED.value
            ),
            error_message=response.error_message,
        )

    async def _claim_and_build(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        now: datetime,
        lease_until: datetime,
    ) -> "_PreparedProcessing | _BuildFailed":
        async with UnitOfWork(self._session_factory) as uow:
            repository = self._repository_factory(uow.session)
            claimed = await repository.claim_outbound_for_processing(
                tenant_id=tenant_id,
                outbound_message_id=outbound_message_id,
                processing_token=processing_token,
                now=now,
                lease_until=lease_until,
            )
            if claimed is None:
                outbound = await repository.get_outbound_by_id(
                    tenant_id,
                    outbound_message_id,
                )
                status = (
                    outbound.internal_status if outbound is not None else "NOT_FOUND"
                )
                raise _ProcessingSkipped(
                    status=status,
                    reason="Outbound message is not claimable for processing.",
                )

            (
                outbound,
                request,
                _template,
                version,
                connection,
                connector,
                message_type,
            ) = await repository.load_processing_context(tenant_id, outbound_message_id)
            try:
                rendered_payload = self._template_renderer.render(
                    version.template_payload,
                    request.variables,
                )
                if not isinstance(rendered_payload, dict):
                    raise CommunicationValidationError(
                        "Rendered template payload must be an object."
                    )
                context = _build_provider_send_context(
                    outbound=outbound,
                    request=request,
                    connection=connection,
                    connector_spec=connector.yaml_spec,
                    send_spec=ProcessOutboundMessageUseCase._resolve_send_spec(
                        connector.yaml_spec,
                        str(message_type.message_type_code),
                    ),
                    provider_message_type_code=str(message_type.message_type_code),
                    rendered_payload=rendered_payload,
                )
                sender = self._sender_registry.get(str(context.send_spec["transport"]))
                prepared = sender.build(context)
                attempt = await repository.create_delivery_attempt(
                    tenant_id=tenant_id,
                    outbound_message_id=outbound.outbound_message_id,
                    provider_connection_id=connection.provider_connection_id,
                    request_payload=prepared.request_payload,
                )
                return _PreparedProcessing(
                    prepared=prepared,
                    context=context,
                    delivery_attempt_id=attempt.delivery_attempt_id,
                    attempt_no=attempt.attempt_no,
                )
            except Exception as exc:
                await repository.fail_outbound_processing(
                    tenant_id=tenant_id,
                    outbound_message_id=outbound_message_id,
                    processing_token=processing_token,
                    delivery_attempt_id=None,
                    error_code=exc.__class__.__name__,
                    error_message=str(exc),
                    finished_at=utc_now(),
                )
                return _BuildFailed(error=exc)

    async def _persist_send_exception(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        delivery_attempt_id: UUID,
        error: Exception,
    ) -> None:
        async with UnitOfWork(self._session_factory) as uow:
            repository = self._repository_factory(uow.session)
            await repository.fail_outbound_processing(
                tenant_id=tenant_id,
                outbound_message_id=outbound_message_id,
                processing_token=processing_token,
                delivery_attempt_id=delivery_attempt_id,
                error_code=error.__class__.__name__,
                error_message=str(error),
                finished_at=utc_now(),
            )

    async def _persist_success(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        delivery_attempt_id: UUID,
        rendered_payload: dict[str, Any],
        prepared: ProviderPreparedSend,
        response: ProviderSendResult,
    ) -> bool:
        async with UnitOfWork(self._session_factory) as uow:
            repository = self._repository_factory(uow.session)
            return await repository.complete_outbound_processing(
                tenant_id=tenant_id,
                outbound_message_id=outbound_message_id,
                processing_token=processing_token,
                delivery_attempt_id=delivery_attempt_id,
                rendered_payload=rendered_payload,
                provider_request_payload=prepared.request_payload,
                response_payload=response.response_payload,
                http_status_code=response.http_status_code,
                external_message_id=response.external_message_id,
                external_status=response.external_status,
                internal_status=response.internal_status,
                finished_at=utc_now(),
            )

    async def _persist_provider_failure(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        processing_token: UUID,
        delivery_attempt_id: UUID,
        response: ProviderSendResult,
        retry_at: datetime | None,
    ) -> bool:
        async with UnitOfWork(self._session_factory) as uow:
            repository = self._repository_factory(uow.session)
            return await repository.fail_outbound_processing(
                tenant_id=tenant_id,
                outbound_message_id=outbound_message_id,
                processing_token=processing_token,
                delivery_attempt_id=delivery_attempt_id,
                error_code=response.error_code or "PROVIDER_FAILED",
                error_message=response.error_message or "Provider send failed.",
                finished_at=utc_now(),
                response_payload=response.response_payload,
                http_status_code=response.http_status_code,
                external_message_id=response.external_message_id,
                external_status=response.external_status,
                retry_at=retry_at,
            )

    @staticmethod
    def _retry_at(
        *,
        connector_spec: dict[str, Any],
        attempt_no: int,
        response: ProviderSendResult,
    ) -> datetime | None:
        if response.http_status_code is None:
            return None
        if response.http_status_code != 429 and response.http_status_code < 500:
            return None
        retry_policy = connector_spec.get("retry_policy") or {}
        max_attempts = int(retry_policy.get("max_attempts") or 1)
        if attempt_no >= max_attempts:
            return None
        backoff = retry_policy.get("backoff") or {}
        initial_seconds = int(backoff.get("initial_seconds") or 30)
        max_seconds = int(backoff.get("max_seconds") or initial_seconds)
        delay = min(initial_seconds * (2 ** max(0, attempt_no - 1)), max_seconds)
        return utc_now() + timedelta(seconds=delay)


class PublishQueuedOutboundMessagesUseCase:
    """Publishes queued outbound messages to the broker."""

    def __init__(
        self,
        *,
        repository: CommunicationRepository,
        publisher: OutboundMessagePublisherProtocol,
        republish_after_seconds: int,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._republish_after_seconds = republish_after_seconds

    async def __call__(
        self,
        command: PublishQueuedOutboundMessagesCommand,
    ) -> PublishQueuedResultDTO:
        now = utc_now()
        outbounds = await self._repository.list_publishable_outbounds(
            tenant_id=command.tenant_id,
            limit=command.limit,
            now=now,
            republish_before=now - timedelta(seconds=self._republish_after_seconds),
        )
        published = 0
        failed = 0
        for outbound in outbounds:
            try:
                await self._publisher.publish(
                    tenant_id=command.tenant_id,
                    outbound_message_id=outbound.outbound_message_id,
                    published_at=now,
                    source=command.source,
                )
                await self._repository.mark_outbound_published(
                    tenant_id=command.tenant_id,
                    outbound_message_id=outbound.outbound_message_id,
                    published_at=now,
                )
                published += 1
            except Exception:
                failed += 1
        return PublishQueuedResultDTO(
            scanned=len(outbounds),
            published=published,
            failed=failed,
        )


class RecoverStuckOutboundMessagesUseCase:
    """Marks expired SENDING messages as UNKNOWN for manual recovery."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        command: RecoverStuckOutboundMessagesCommand,
    ) -> RecoverStuckResultDTO:
        now = utc_now()
        recovered = await self._repository.recover_stuck_outbounds(
            tenant_id=command.tenant_id,
            older_than=now - timedelta(seconds=command.older_than_seconds),
            now=now,
            limit=command.limit,
        )
        return RecoverStuckResultDTO(recovered=recovered)


class HandleProviderWebhookUseCase:
    """Handles provider delivery webhooks using connector YAML mappings."""

    def __init__(
        self,
        repository: CommunicationRepository,
        json_path: JsonPathService,
        status_mapper: ProviderStatusMappingService,
    ) -> None:
        self._repository = repository
        self._json_path = json_path
        self._status_mapper = status_mapper

    async def __call__(
        self,
        command: HandleProviderWebhookCommand,
    ) -> WebhookResultDTO:
        connector = await self._repository.get_active_connector_by_code(
            command.tenant_id, command.provider_code
        )
        if connector is None:
            raise CommunicationNotFoundError("Provider connector was not found.")
        webhook_spec = connector.yaml_spec.get("webhook") or {}
        external_message_id = self._json_path.extract_one(
            command.raw_payload,
            webhook_spec.get("external_message_id_path"),
        )
        external_status = self._json_path.extract_one(
            command.raw_payload,
            webhook_spec.get("external_status_path"),
        )
        if external_message_id is None:
            raise CommunicationValidationError(
                "Webhook payload does not contain external message id."
            )
        outbound = await self._repository.find_outbound_by_external_message_id(
            tenant_id=command.tenant_id,
            external_message_id=str(external_message_id),
        )
        if outbound is None:
            return WebhookResultDTO(
                accepted=True,
                matched=False,
                outbound_message_id=None,
                internal_status=None,
            )
        internal_status = self._status_mapper.map_status(
            connector.yaml_spec.get("status_mapping"),
            external_status,
        )
        event_at = _parse_event_time(
            self._json_path.extract_one(
                command.raw_payload,
                webhook_spec.get("event_time_path"),
            )
        )
        await self._repository.add_delivery_event(
            tenant_id=command.tenant_id,
            outbound_message_id=outbound.outbound_message_id,
            provider_connection_id=outbound.provider_connection_id,
            external_message_id=str(external_message_id),
            external_status=(
                str(external_status) if external_status is not None else None
            ),
            internal_status=internal_status,
            event_type=_event_type_for_status(internal_status),
            event_at=event_at,
            raw_payload=command.raw_payload,
        )
        now = utc_now()
        await self._repository.update_outbound_status_from_event(
            tenant_id=command.tenant_id,
            outbound_message_id=outbound.outbound_message_id,
            external_status=(
                str(external_status) if external_status is not None else None
            ),
            internal_status=internal_status,
            now=now,
        )
        return WebhookResultDTO(
            accepted=True,
            matched=True,
            outbound_message_id=outbound.outbound_message_id,
            internal_status=internal_status,
        )


class GetOutboundMessageUseCase:
    """Returns one outbound message."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
    ) -> OutboundMessageDTO:
        outbound = await self._repository.get_outbound(
            tenant_id=tenant_id,
            outbound_message_id=outbound_message_id,
        )
        if outbound is None:
            raise CommunicationNotFoundError("Outbound message was not found.")
        return outbound_to_dto(outbound)


class ListOutboundMessagesUseCase:
    """Returns tenant outbound message history."""

    def __init__(self, repository: CommunicationRepository) -> None:
        self._repository = repository

    async def __call__(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        offset: int,
    ) -> list[OutboundMessageDTO]:
        return [
            outbound_to_dto(item)
            for item in await self._repository.list_outbound(
                tenant_id=tenant_id,
                limit=limit,
                offset=offset,
            )
        ]


class _ProcessingSkipped(Exception):
    def __init__(self, *, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _PreparedProcessing:
    prepared: ProviderPreparedSend
    context: ProviderSendContext
    delivery_attempt_id: UUID
    attempt_no: int


@dataclass(frozen=True, slots=True)
class _BuildFailed:
    error: Exception


def _build_provider_send_context(
    *,
    outbound,
    request,
    connection,
    connector_spec: dict[str, Any],
    send_spec: dict[str, Any],
    provider_message_type_code: str,
    rendered_payload: dict[str, Any],
) -> ProviderSendContext:
    return ProviderSendContext(
        outbound_message_id=outbound.outbound_message_id,
        communication_request_id=request.communication_request_id,
        initiator_ref_id=request.initiator_ref_id,
        recipient_address=outbound.recipient_address,
        recipient_snapshot=request.recipient_snapshot,
        variables=request.variables,
        connection_code=connection.connection_code,
        channel_code=connection.channel_code,
        provider_message_type_code=provider_message_type_code,
        config=connection.config,
        secrets_b64=connection.secrets_b64,
        connector_spec=connector_spec,
        send_spec=send_spec,
        rendered_payload=rendered_payload,
    )


def _event_type_for_status(internal_status: str) -> str:
    if internal_status in {item.value for item in DeliveryEventType}:
        return internal_status
    return DeliveryEventType.WEBHOOK_RECEIVED.value


def _parse_event_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


__all__ = [
    "ActivateTemplateVersionCommand",
    "ActivateTemplateVersionUseCase",
    "CreateMessageTemplateCommand",
    "CreateMessageTemplateUseCase",
    "CreateProviderConnectionCommand",
    "CreateProviderConnectionUseCase",
    "CreateTemplateVersionCommand",
    "CreateTemplateVersionUseCase",
    "GetOutboundMessageUseCase",
    "HandleProviderWebhookCommand",
    "HandleProviderWebhookUseCase",
    "ListMessageTemplatesUseCase",
    "ListOutboundMessagesUseCase",
    "ListProviderConnectionsUseCase",
    "ListProviderConnectorsUseCase",
    "ProcessOutboundMessageByIdCommand",
    "ProcessOutboundMessageByIdUseCase",
    "ProcessOutboundMessageUseCase",
    "ProcessQueuedMessagesCommand",
    "PublishQueuedOutboundMessagesCommand",
    "PublishQueuedOutboundMessagesUseCase",
    "RecoverStuckOutboundMessagesCommand",
    "RecoverStuckOutboundMessagesUseCase",
    "RegisterProviderConnectorCommand",
    "RegisterProviderConnectorUseCase",
    "SendCommunicationCommand",
    "SendCommunicationUseCase",
]
