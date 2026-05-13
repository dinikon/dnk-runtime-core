from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.modules.communication.application.delivery.command import (
    HandleProviderWebhookCommand,
)
from src.modules.communication.application.delivery.dto import WebhookResultDTO
from src.modules.communication.application.services import (
    JsonPathService,
    ProviderStatusMappingService,
)
from src.modules.communication.domain.delivery import (
    DeliveryService,
    ExternalMessageId,
    WebhookPayloadValidationError,
)
from src.modules.communication.domain.delivery.repository import (
    DeliveryWebhookLookupProtocol,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorNotFoundError,
)


class HandleProviderWebhookUseCase:
    """Use case обработки provider delivery webhook."""

    def __init__(
        self,
        *,
        repository: DeliveryWebhookLookupProtocol,
        service: DeliveryService,
        json_path: JsonPathService,
        status_mapper: ProviderStatusMappingService,
    ) -> None:
        """Инициализирует use case delivery repository и mapping services."""
        self._repository = repository
        self._service = service
        self._json_path = json_path
        self._status_mapper = status_mapper

    async def __call__(
        self,
        command: HandleProviderWebhookCommand,
    ) -> WebhookResultDTO:
        """Принимает provider webhook и обновляет delivery state."""
        connector = await self._repository.get_active_connector_by_code(
            tenant_id=command.tenant_id,
            provider_code=command.provider_code,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()

        webhook_spec = connector.yaml_spec.get("webhook") or {}
        external_message_id = self._external_message_id(
            self._json_path.extract_one(
                command.raw_payload,
                webhook_spec.get("external_message_id_path"),
            )
        )
        external_status_raw = self._json_path.extract_one(
            command.raw_payload,
            webhook_spec.get("external_status_path"),
        )
        external_status = (
            None if external_status_raw is None else str(external_status_raw)
        )
        outbound = await self._repository.find_outbound_by_external_message_id(
            tenant_id=command.tenant_id,
            external_message_id=external_message_id,
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
            external_status_raw,
        )
        await self._service.record_webhook_event(
            tenant_id=command.tenant_id,
            delivery_event_id=command.delivery_event_id,
            outbound=outbound,
            external_message_id=external_message_id,
            external_status=external_status,
            internal_status=internal_status,
            event_at=_parse_event_time(
                self._json_path.extract_one(
                    command.raw_payload,
                    webhook_spec.get("event_time_path"),
                )
            ),
            raw_payload=command.raw_payload,
        )
        return WebhookResultDTO(
            accepted=True,
            matched=True,
            outbound_message_id=outbound.outbound_message_id.uuid,
            internal_status=internal_status,
        )

    @staticmethod
    def _external_message_id(value: Any) -> str:
        """Достает и валидирует external message id из webhook payload."""
        if value is None:
            raise WebhookPayloadValidationError(
                "Webhook payload does not contain external message id."
            )
        return ExternalMessageId(str(value)).value


def _parse_event_time(value: Any) -> datetime | None:
    """Парсит provider event timestamp в datetime, если формат поддержан."""
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


__all__ = ["HandleProviderWebhookUseCase"]
