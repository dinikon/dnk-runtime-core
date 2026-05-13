from src.modules.communication.application.outbound_message.command import (
    ProcessQueuedMessagesCommand,
)
from src.modules.communication.application.outbound_message.dto import (
    ProcessQueuedResultDTO,
)
from src.modules.communication.application.outbound_message.processing.ports import (
    OutboundProcessingRepositoryProtocol,
)
from src.modules.communication.application.outbound_message.provider_send import (
    ProviderSenderRegistryProtocol,
    build_provider_send_context,
    id_uuid,
    resolve_send_spec,
)
from src.modules.communication.application.services import TemplateRenderService
from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.outbound_message import OutboundMessageIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.kernel.time.ports import ClockPort


class ProcessOutboundMessageUseCase:
    """Use case batch processing queued outbound messages."""

    def __init__(
        self,
        repository: OutboundProcessingRepositoryProtocol,
        sender_registry: ProviderSenderRegistryProtocol,
        template_renderer: TemplateRenderService,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case processing repository и provider sender registry."""
        self._repository = repository
        self._sender_registry = sender_registry
        self._template_renderer = template_renderer
        self._clock = clock

    async def __call__(
        self,
        command: ProcessQueuedMessagesCommand,
    ) -> ProcessQueuedResultDTO:
        """Захватывает queued messages и обрабатывает их через provider senders."""
        tenant_id = _entity_id(command.tenant_id)
        queued = await self._repository.claim_queued_messages(
            tenant_id,
            command.limit,
        )
        succeeded = 0
        failed = 0
        for message in queued:
            try:
                await self._process_one(
                    tenant_id,
                    OutboundMessageIdVO.from_value(
                        id_uuid(message.outbound_message_id)
                    ),
                )
                succeeded += 1
            except Exception:
                failed += 1
        return ProcessQueuedResultDTO(
            processed=len(queued),
            succeeded=succeeded,
            failed=failed,
        )

    async def _process_one(
        self,
        tenant_id: EntityIdVO,
        outbound_message_id: OutboundMessageIdVO,
    ) -> None:
        (
            outbound,
            request,
            _template,
            version,
            connection,
            connector,
            message_type,
        ) = await self._repository.load_processing_context(
            tenant_id,
            outbound_message_id,
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


def _entity_id(value) -> EntityIdVO:
    if type(value) is EntityIdVO:
        return value
    return EntityIdVO.from_value(value)


__all__ = ["ProcessOutboundMessageUseCase"]
