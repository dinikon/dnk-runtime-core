from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from src.modules.communication.application.outbound_message.command import (
    ProcessOutboundMessageByIdCommand,
)
from src.modules.communication.application.outbound_message.dto import (
    ProcessOutboundMessageResultDTO,
)
from src.modules.communication.application.outbound_message.processing.ports import (
    OutboundProcessingRepositoryContextFactoryProtocol,
)
from src.modules.communication.application.outbound_message.provider_send import (
    ProviderPreparedSend,
    ProviderSendContext,
    ProviderSendResult,
    ProviderSenderRegistryProtocol,
    build_provider_send_context,
    id_uuid,
    resolve_send_spec,
)
from src.modules.communication.application.services import TemplateRenderService
from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.outbound_message import (
    OutboundMessageIdVO,
    OutboundMessageStatus,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class ProcessOutboundMessageByIdUseCase:
    """Use case обработки одного outbound message с короткими transaction scopes."""

    def __init__(
        self,
        *,
        repository_context_factory: OutboundProcessingRepositoryContextFactoryProtocol,
        sender_registry: ProviderSenderRegistryProtocol,
        template_renderer: TemplateRenderService,
        processing_lease_seconds: int,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case transaction-scoped repository factory."""
        self._repository_context_factory = repository_context_factory
        self._sender_registry = sender_registry
        self._template_renderer = template_renderer
        self._processing_lease_seconds = processing_lease_seconds
        self._clock = clock

    async def __call__(
        self,
        command: ProcessOutboundMessageByIdCommand,
    ) -> ProcessOutboundMessageResultDTO:
        """Обрабатывает один outbound message с lease-token защитой."""
        tenant_id = _entity_id(command.tenant_id)
        outbound_message_id = _outbound_id(command.outbound_message_id)
        token = EntityIdVO.from_value(uuid4())
        now = self._clock.now()
        lease_until = now + timedelta(seconds=self._processing_lease_seconds)

        try:
            claimed = await self._claim_and_build(
                tenant_id=tenant_id,
                outbound_message_id=outbound_message_id,
                processing_token=token,
                now=now,
                lease_until=lease_until,
            )
        except _ProcessingSkipped as skipped:
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=outbound_message_id.uuid,
                processed=False,
                succeeded=False,
                skipped=True,
                status=skipped.status,
                error_message=skipped.reason,
            )
        if isinstance(claimed, _BuildFailed):
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=outbound_message_id.uuid,
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
                outbound_message_id=outbound_message_id,
                tenant_id=tenant_id,
                processing_token=token,
                delivery_attempt_id=attempt_id,
                error=exc,
            )
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=outbound_message_id.uuid,
                processed=True,
                succeeded=False,
                skipped=False,
                status=OutboundMessageStatus.FAILED.value,
                error_message=str(exc),
            )

        if response.success:
            applied = await self._persist_success(
                outbound_message_id=outbound_message_id,
                tenant_id=tenant_id,
                processing_token=token,
                delivery_attempt_id=attempt_id,
                rendered_payload=send_context.rendered_payload,
                prepared=prepared,
                response=response,
            )
            return ProcessOutboundMessageResultDTO(
                outbound_message_id=outbound_message_id.uuid,
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
            outbound_message_id=outbound_message_id,
            tenant_id=tenant_id,
            processing_token=token,
            delivery_attempt_id=attempt_id,
            response=response,
            retry_at=retry_at,
        )
        return ProcessOutboundMessageResultDTO(
            outbound_message_id=outbound_message_id.uuid,
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
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        now: datetime,
        lease_until: datetime,
    ) -> "_PreparedProcessing | _BuildFailed":
        async with self._repository_context_factory() as repository:
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
                connection.ensure_active()
                connector.ensure_active()
                rendered_payload = self._template_renderer.render(
                    version.template_payload,
                    request.variables,
                )
                if not isinstance(rendered_payload, dict):
                    raise CommunicationValidationError(
                        "Rendered template payload must be an object."
                    )
                context = build_provider_send_context(
                    outbound=outbound,
                    request=request,
                    connection=connection,
                    connector_spec=connector.yaml_spec,
                    send_spec=resolve_send_spec(
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
                    finished_at=self._clock.now(),
                )
                return _BuildFailed(error=exc)

    async def _persist_send_exception(
        self,
        *,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        delivery_attempt_id,
        error: Exception,
    ) -> None:
        async with self._repository_context_factory() as repository:
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
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        delivery_attempt_id,
        rendered_payload: dict[str, Any],
        prepared: ProviderPreparedSend,
        response: ProviderSendResult,
    ) -> bool:
        async with self._repository_context_factory() as repository:
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
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
        processing_token: EntityIdVO,
        delivery_attempt_id,
        response: ProviderSendResult,
        retry_at: datetime | None,
    ) -> bool:
        async with self._repository_context_factory() as repository:
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


class _ProcessingSkipped(Exception):
    def __init__(self, *, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True, slots=True)
class _PreparedProcessing:
    prepared: ProviderPreparedSend
    context: ProviderSendContext
    delivery_attempt_id: Any
    attempt_no: int


@dataclass(frozen=True, slots=True)
class _BuildFailed:
    error: Exception


def _entity_id(value: Any) -> EntityIdVO:
    if type(value) is EntityIdVO:
        return value
    return EntityIdVO.from_value(value)


def _outbound_id(value: Any) -> OutboundMessageIdVO:
    if type(value) is OutboundMessageIdVO:
        return value
    return OutboundMessageIdVO.from_value(value)


__all__ = ["ProcessOutboundMessageByIdUseCase"]
