from src.modules.channels.application.content_delivery.command.request_content_delivery.command import (
    RequestContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.command.request_content_delivery.dto import (
    RequestContentDeliveryResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class RequestContentDeliveryHandler:
    """Координирует request_content_delivery в общем внешнем UoW."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Получает сервис с конкретными портами без доступа к SQL."""
        self._service = service

    async def execute(
        self, command: RequestContentDeliveryCommand
    ) -> RequestContentDeliveryResultDTO:
        """Передаёт явные параметры и возвращает собственный DTO сценария."""
        result = await self._service.request(
            tenant_id=command.tenant_id,
            actor_id=command.actor_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            expected_revision=command.expected_revision,
            expected_binding_revision=command.expected_binding_revision,
            expected_config_revision=command.expected_config_revision,
            fingerprint=command.fingerprint,
        )
        return RequestContentDeliveryResultDTO(result)
