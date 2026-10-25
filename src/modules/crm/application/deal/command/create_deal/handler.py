from src.modules.crm.application.deal.command.create_deal.command import (
    CreateDealCommand,
)
from src.modules.crm.application.deal.command.create_deal.dto import CreateDealResultDTO
from src.modules.crm.application.deal.service.mutations import DealMutationService


class CreateDealHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: DealMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(self, command: CreateDealCommand) -> CreateDealResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.create(command)
        return CreateDealResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
