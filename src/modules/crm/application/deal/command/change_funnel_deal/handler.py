from src.modules.crm.application.deal.command.change_funnel_deal.command import (
    ChangeDealFunnelCommand,
)
from src.modules.crm.application.deal.command.change_funnel_deal.dto import (
    ChangeDealFunnelResultDTO,
)
from src.modules.crm.application.deal.service.mutations import DealMutationService


class ChangeDealFunnelHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: DealMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(
        self, command: ChangeDealFunnelCommand
    ) -> ChangeDealFunnelResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.change_funnel(command)
        return ChangeDealFunnelResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
