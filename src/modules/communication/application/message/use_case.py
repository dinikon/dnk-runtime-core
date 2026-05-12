from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.communication.application.message.command import (
    ProcessOutboundMessageByIdCommand,
    ProcessQueuedMessagesCommand,
    SendCommunicationCommand,
)
from src.modules.communication.application.message.dto import (
    OutboundMessageDTO,
    ProcessOutboundMessageResultDTO,
    ProcessQueuedResultDTO,
    SendCommunicationResultDTO,
)
from src.modules.communication.application.message.ports import (
    CommunicationRepositoryFactory,
    OutboundMessageQueryRepositoryProtocol,
    OutboundProcessingRepositoryProtocol,
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderRegistryProtocol,
    SendCommunicationRepositoryProtocol,
)
from src.modules.communication.application.services import (
    JsonSchemaValidationService,
    TemplateRenderService,
)
from src.modules.communication.domain.error import (
    CommunicationValidationError,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateNotFoundError,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessageNotFoundError,
    OutboundMessageStatus,
)
from src.modules.shared.db.uow import UnitOfWork
from src.modules.shared.kernel.time.ports import ClockPort


class SendCommunicationUseCase:
    """Accepts a send request and creates an outbound message for the worker."""

    def __init__(
        self,
        repository: SendCommunicationRepositoryProtocol,
        schema_validator: JsonSchemaValidationService,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._schema_validator = schema_validator
        self._clock = clock

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
                    communication_request_id=_id_uuid(request.communication_request_id),
                    outbound_message_id=_id_uuid(outbound.outbound_message_id),
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
            raise MessageTemplateNotFoundError()
        if template.channel_code != command.channel_code:
            raise CommunicationValidationError(
                "Send channel must match template channel."
            )
        active_version = await self._repository.get_active_template_version(
            command.tenant_id,
            _id_uuid(template.template_id),
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
            provider_connector_id=_id_uuid(template.provider_connector_id),
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
            template_id=_id_uuid(template.template_id),
            template_version_id=_id_uuid(active_version.template_version_id),
            contact_id=command.contact_id,
            recipient_address=command.recipient_address,
            recipient_snapshot=command.recipient_snapshot,
            variables=command.variables,
            scheduled_at=command.scheduled_at,
            priority=command.priority,
            provider_connection_id=_id_uuid(connection.provider_connection_id),
            now=self._clock.now(),
        )
        return SendCommunicationResultDTO(
            communication_request_id=_id_uuid(request.communication_request_id),
            outbound_message_id=_id_uuid(outbound.outbound_message_id),
            status=request.status,
            internal_status=outbound.internal_status,
            idempotent=False,
        )


class ProcessOutboundMessageUseCase:
    """Processes queued outbound messages through provider sender transports."""

    def __init__(
        self,
        repository: OutboundProcessingRepositoryProtocol,
        sender_registry: ProviderSenderRegistryProtocol,
        template_renderer: TemplateRenderService,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._sender_registry = sender_registry
        self._template_renderer = template_renderer
        self._clock = clock

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
                await self._process_one(
                    command.tenant_id,
                    _id_uuid(message.outbound_message_id),
                )
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
        now = self._clock.now()
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
            context = _build_provider_send_context(
                outbound=outbound,
                request=request,
                connection=connection,
                connector_spec=connector.yaml_spec,
                send_spec=_resolve_send_spec(
                    connector.yaml_spec,
                    str(message_type.message_type_code),
                ),
                provider_message_type_code=str(message_type.message_type_code),
                rendered_payload=rendered_payload,
            )
            sender = self._sender_registry.get(str(context.send_spec["transport"]))
            prepared = sender.build(context)
            attempt = await self._repository.create_delivery_attempt(
                tenant_id=tenant_id,
                outbound_message_id=_id_uuid(outbound.outbound_message_id),
                provider_connection_id=_id_uuid(connection.provider_connection_id),
                request_payload=prepared.request_payload,
            )
            response = await sender.send(context, prepared)
            if response.success:
                await self._repository.complete_outbound_processing(
                    tenant_id=tenant_id,
                    outbound_message_id=_id_uuid(outbound.outbound_message_id),
                    processing_token=_id_uuid(outbound.processing_token),
                    delivery_attempt_id=_id_uuid(attempt.delivery_attempt_id),
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
                    outbound_message_id=_id_uuid(outbound.outbound_message_id),
                    processing_token=_id_uuid(outbound.processing_token),
                    delivery_attempt_id=_id_uuid(attempt.delivery_attempt_id),
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
                outbound_message_id=_id_uuid(outbound.outbound_message_id),
                processing_token=_id_uuid(outbound.processing_token),
                delivery_attempt_id=(
                    _id_uuid(attempt.delivery_attempt_id)
                    if attempt is not None
                    else None
                ),
                error_code=exc.__class__.__name__,
                error_message=str(exc),
                finished_at=now,
            )
            raise


class ProcessOutboundMessageByIdUseCase:
    """Processes one outbound message with short DB transactions and a lease."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repository_factory: CommunicationRepositoryFactory,
        sender_registry: ProviderSenderRegistryProtocol,
        template_renderer: TemplateRenderService,
        processing_lease_seconds: int,
        clock: ClockPort,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._sender_registry = sender_registry
        self._template_renderer = template_renderer
        self._processing_lease_seconds = processing_lease_seconds
        self._clock = clock

    async def __call__(
        self,
        command: ProcessOutboundMessageByIdCommand,
    ) -> ProcessOutboundMessageResultDTO:
        token = uuid4()
        now = self._clock.now()
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
                    send_spec=_resolve_send_spec(
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
                    outbound_message_id=_id_uuid(outbound.outbound_message_id),
                    provider_connection_id=_id_uuid(connection.provider_connection_id),
                    request_payload=prepared.request_payload,
                )
                return _PreparedProcessing(
                    prepared=prepared,
                    context=context,
                    delivery_attempt_id=_id_uuid(attempt.delivery_attempt_id),
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
                    finished_at=self._clock.now(),
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
                finished_at=self._clock.now(),
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
                finished_at=self._clock.now(),
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
                finished_at=self._clock.now(),
                response_payload=response.response_payload,
                http_status_code=response.http_status_code,
                external_message_id=response.external_message_id,
                external_status=response.external_status,
                retry_at=retry_at,
            )

    def _retry_at(
        self,
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
        return self._clock.now() + timedelta(seconds=delay)


class GetOutboundMessageUseCase:
    """Returns one outbound message."""

    def __init__(self, repository: OutboundMessageQueryRepositoryProtocol) -> None:
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
            raise OutboundMessageNotFoundError()
        return OutboundMessageDTO(
            outbound_message_id=_id_uuid(outbound.outbound_message_id),
            tenant_id=_id_uuid(outbound.tenant_id),
            communication_request_id=_id_uuid(outbound.communication_request_id),
            provider_connection_id=_id_uuid(outbound.provider_connection_id),
            channel_code=outbound.channel_code,
            contact_id=(
                None if outbound.contact_id is None else _id_uuid(outbound.contact_id)
            ),
            recipient_address=outbound.recipient_address,
            rendered_payload=dict(outbound.rendered_payload or {}),
            provider_request_payload=dict(outbound.provider_request_payload or {}),
            external_message_id=outbound.external_message_id,
            external_status=outbound.external_status,
            internal_status=outbound.internal_status,
            error_code=outbound.error_code,
            error_message=outbound.error_message,
            queued_at=outbound.queued_at,
            sent_at=outbound.sent_at,
            delivered_at=outbound.delivered_at,
            failed_at=outbound.failed_at,
            created_at=outbound.created_at,
            updated_at=outbound.updated_at,
        )


class ListOutboundMessagesUseCase:
    """Returns tenant outbound message history."""

    def __init__(self, repository: OutboundMessageQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        offset: int,
    ) -> list[OutboundMessageDTO]:
        result = []
        for outbound in await self._repository.list_outbound(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        ):
            result.append(
                OutboundMessageDTO(
                    outbound_message_id=_id_uuid(outbound.outbound_message_id),
                    tenant_id=_id_uuid(outbound.tenant_id),
                    communication_request_id=_id_uuid(
                        outbound.communication_request_id
                    ),
                    provider_connection_id=_id_uuid(outbound.provider_connection_id),
                    channel_code=outbound.channel_code,
                    contact_id=(
                        None
                        if outbound.contact_id is None
                        else _id_uuid(outbound.contact_id)
                    ),
                    recipient_address=outbound.recipient_address,
                    rendered_payload=dict(outbound.rendered_payload or {}),
                    provider_request_payload=dict(
                        outbound.provider_request_payload or {}
                    ),
                    external_message_id=outbound.external_message_id,
                    external_status=outbound.external_status,
                    internal_status=outbound.internal_status,
                    error_code=outbound.error_code,
                    error_message=outbound.error_message,
                    queued_at=outbound.queued_at,
                    sent_at=outbound.sent_at,
                    delivered_at=outbound.delivered_at,
                    failed_at=outbound.failed_at,
                    created_at=outbound.created_at,
                    updated_at=outbound.updated_at,
                )
            )
        return result


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
        outbound_message_id=_id_uuid(outbound.outbound_message_id),
        communication_request_id=_id_uuid(request.communication_request_id),
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


def parse_event_time(value: Any) -> datetime | None:
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


def _id_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if hasattr(value, "uuid"):
        return value.uuid
    raise TypeError("Communication id value must expose UUID.")


__all__ = [
    "GetOutboundMessageUseCase",
    "ListOutboundMessagesUseCase",
    "ProcessOutboundMessageByIdCommand",
    "ProcessOutboundMessageByIdUseCase",
    "ProcessOutboundMessageUseCase",
    "ProcessQueuedMessagesCommand",
    "SendCommunicationCommand",
    "SendCommunicationUseCase",
    "parse_event_time",
]
