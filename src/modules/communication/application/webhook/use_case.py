from __future__ import annotations

from typing import Any
from uuid import UUID

from src.modules.communication.application.message.use_case import parse_event_time
from src.modules.communication.application.services import (
    JsonPathService,
    ProviderStatusMappingService,
)
from src.modules.communication.application.webhook.command import (
    HandleProviderWebhookCommand,
)
from src.modules.communication.application.webhook.dto import WebhookResultDTO
from src.modules.communication.application.webhook.ports import (
    ProviderWebhookRepositoryProtocol,
)
from src.modules.communication.domain import (
    CommunicationValidationError,
    DeliveryEventType,
    ProviderConnectorNotFoundError,
)
from src.modules.shared.kernel.time.ports import ClockPort


class HandleProviderWebhookUseCase:
    """Handles provider delivery webhooks using connector YAML mappings."""

    def __init__(
        self,
        repository: ProviderWebhookRepositoryProtocol,
        json_path: JsonPathService,
        status_mapper: ProviderStatusMappingService,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._json_path = json_path
        self._status_mapper = status_mapper
        self._clock = clock

    async def __call__(
        self,
        command: HandleProviderWebhookCommand,
    ) -> WebhookResultDTO:
        connector = await self._repository.get_active_connector_by_code(
            command.tenant_id,
            command.provider_code,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()
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
        event_at = parse_event_time(
            self._json_path.extract_one(
                command.raw_payload,
                webhook_spec.get("event_time_path"),
            )
        )
        await self._repository.add_delivery_event(
            tenant_id=command.tenant_id,
            outbound_message_id=_id_uuid(outbound.outbound_message_id),
            provider_connection_id=_id_uuid(outbound.provider_connection_id),
            external_message_id=str(external_message_id),
            external_status=(
                str(external_status) if external_status is not None else None
            ),
            internal_status=internal_status,
            event_type=_event_type_for_status(internal_status),
            event_at=event_at,
            raw_payload=command.raw_payload,
        )
        await self._repository.update_outbound_status_from_event(
            tenant_id=command.tenant_id,
            outbound_message_id=_id_uuid(outbound.outbound_message_id),
            external_status=(
                str(external_status) if external_status is not None else None
            ),
            internal_status=internal_status,
            now=self._clock.now(),
        )
        return WebhookResultDTO(
            accepted=True,
            matched=True,
            outbound_message_id=_id_uuid(outbound.outbound_message_id),
            internal_status=internal_status,
        )


def _event_type_for_status(internal_status: str) -> str:
    if internal_status in {item.value for item in DeliveryEventType}:
        return internal_status
    return DeliveryEventType.WEBHOOK_RECEIVED.value


def _id_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if hasattr(value, "uuid"):
        return value.uuid
    raise TypeError("Communication id value must expose UUID.")


__all__ = ["HandleProviderWebhookUseCase"]
