from src.modules.channels.application.content_delivery.command.resolve_content_uncertainty.command import (
    ResolveContentUncertaintyCommand,
)
from src.modules.channels.application.content_delivery.command.resolve_content_uncertainty.dto import (
    ResolveContentUncertaintyResultDTO,
)
from src.modules.channels.application.content_delivery.service import ContentDeliveries


class ResolveContentUncertaintyHandler:
    """Координирует явное завершение попытки внутри общего внешнего UoW."""

    def __init__(self, service: ContentDeliveries) -> None:
        """Получает Application-сервис без инфраструктурной сессии."""
        self._service = service

    async def execute(
        self, command: ResolveContentUncertaintyCommand
    ) -> ResolveContentUncertaintyResultDTO:
        """Передаёт проверенный ввод и возвращает конкретный результат сценария."""
        rows = await self._service.resolve(
            tenant_id=command.tenant_id,
            actor_id=command.actor_id,
            channel_id=command.channel_id,
            group_id=command.group_id,
            publication_id=command.publication_id,
            expected_revision=command.expected_revision,
            acknowledge_unconfirmed=command.acknowledge_unconfirmed,
        )
        return ResolveContentUncertaintyResultDTO(rows)
