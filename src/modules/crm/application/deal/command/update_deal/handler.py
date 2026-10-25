from src.modules.crm.application.deal.command.update_deal.command import (
    UpdateDealCommand,
)
from src.modules.crm.application.deal.command.update_deal.dto import UpdateDealResultDTO
from src.modules.crm.application.deal.service.mutations import DealMutationService


class UpdateDealHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: DealMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(self, command: UpdateDealCommand) -> UpdateDealResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.update(command)
        return UpdateDealResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
