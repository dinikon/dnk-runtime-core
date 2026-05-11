from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.modules.communication.application.dto import (
    MessageTemplateDTO,
    OutboundMessageDTO,
    ProcessQueuedResultDTO,
    ProviderConnectionDTO,
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
    SendCommunicationResultDTO,
    TemplateVersionDTO,
    WebhookResultDTO,
)
from src.modules.communication.application.ports import (
    ProviderSendContext,
    ProviderSenderRegistryProtocol,
)
from src.modules.communication.application.services import (
    JsonSchemaValidationService,
    ProviderStatusMappingService,
    ProviderYamlLoader,
    TemplateRenderService,
)
from src.modules.communication.domain import (
    AttemptStatus,
    CommunicationNotFoundError,
    CommunicationValidationError,
    DeliveryEventType,
    OutboundMessageStatus,
    RequestStatus,
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


@dataclass(frozen=True, slots=True)
class RegisterProviderConnectorCommand:
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
    limit: int = 100


@dataclass(frozen=True, slots=True)
class HandleProviderWebhookCommand:
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
            provider_code=str(spec["provider_code"]),
            provider_name=str(spec["provider_name"]),
            version=str(spec["version"]),
            connector_type=str(spec["connector_type"]),
            yaml_spec=spec,
            yaml_checksum=parsed.checksum,
        )
        for message_type in spec["message_types"]:
            await self._repository.upsert_message_type(
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
    ) -> tuple[list[ProviderConnectorDTO], list[ProviderMessageTypeDTO]]:
        connectors = [
            connector_to_dto(item) for item in await self._repository.list_connectors()
        ]
        message_types = [
            message_type_to_dto(item)
            for item in await self._repository.list_message_types()
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
        connector = await self._repository.get_connector(command.provider_connector_id)
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
        connector = await self._repository.get_connector(command.provider_connector_id)
        if connector is None:
            raise CommunicationNotFoundError("Provider connector was not found.")
        message_type = await self._repository.get_message_type(
            command.provider_message_type_id
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
            template.provider_message_type_id
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
            command.template_version_id
        )
        if version is None or version.template_id != template.template_id:
            raise CommunicationNotFoundError("Template version was not found.")
        activated = await self._repository.activate_template_version(
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
                template.template_id
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
            template.template_id
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
        queued = await self._repository.claim_queued_messages(command.limit)
        succeeded = 0
        failed = 0
        for message in queued:
            try:
                await self._process_one(message.outbound_message_id)
                succeeded += 1
            except Exception:
                failed += 1
        return ProcessQueuedResultDTO(
            processed=len(queued),
            succeeded=succeeded,
            failed=failed,
        )

    async def _process_one(self, outbound_message_id: UUID) -> None:
        (
            outbound,
            request,
            _template,
            version,
            connection,
            connector,
        ) = await self._repository.load_processing_context(outbound_message_id)
        now = utc_now()
        outbound.internal_status = OutboundMessageStatus.SENDING.value
        request.status = RequestStatus.PROCESSING.value
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
                rendered_payload=rendered_payload,
            )
            send_spec = connector.yaml_spec["send"]
            sender = self._sender_registry.get(str(send_spec["transport"]))
            prepared = sender.build(context)
            attempt = await self._repository.create_delivery_attempt(
                outbound_message_id=outbound.outbound_message_id,
                provider_connection_id=connection.provider_connection_id,
                request_payload=prepared.request_payload,
            )
            response = await sender.send(context, prepared)

            outbound.rendered_payload = rendered_payload
            outbound.provider_request_payload = prepared.request_payload
            outbound.external_message_id = response.external_message_id
            outbound.external_status = response.external_status
            outbound.internal_status = response.internal_status
            self._apply_status_timestamps(outbound, response.internal_status, now)
            request.status = (
                RequestStatus.COMPLETED.value
                if response.success
                else RequestStatus.FAILED.value
            )
            if not response.success:
                outbound.error_code = response.error_code
                outbound.error_message = response.error_message
            attempt.status = (
                AttemptStatus.SUCCESS.value
                if response.success
                else AttemptStatus.NON_RETRYABLE_FAILED.value
            )
            attempt.response_payload = response.response_payload
            attempt.http_status_code = response.http_status_code
            attempt.external_message_id = response.external_message_id
            attempt.finished_at = now
        except Exception as exc:
            if attempt is not None:
                attempt.status = AttemptStatus.NON_RETRYABLE_FAILED.value
                attempt.response_payload = {"error": str(exc)}
                attempt.error_code = exc.__class__.__name__
                attempt.error_message = str(exc)
                attempt.finished_at = now
            outbound.internal_status = OutboundMessageStatus.FAILED.value
            outbound.error_code = exc.__class__.__name__
            outbound.error_message = str(exc)
            outbound.failed_at = now
            request.status = RequestStatus.FAILED.value
            raise

    def _build_render_context(
        self,
        *,
        outbound,
        request,
        connection,
        connector_spec: dict[str, Any],
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
            config=connection.config,
            secrets_b64=connection.secrets_b64,
            connector_spec=connector_spec,
            rendered_payload=rendered_payload,
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
            command.provider_code
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
            str(external_message_id)
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
            tenant_id=outbound.tenant_id,
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
        outbound.external_status = (
            str(external_status) if external_status is not None else None
        )
        outbound.internal_status = internal_status
        ProcessOutboundMessageUseCase._apply_status_timestamps(
            outbound,
            internal_status,
            now,
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
    "ProcessOutboundMessageUseCase",
    "ProcessQueuedMessagesCommand",
    "RegisterProviderConnectorCommand",
    "RegisterProviderConnectorUseCase",
    "SendCommunicationCommand",
    "SendCommunicationUseCase",
]
