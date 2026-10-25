from src.modules.crm.application.deal.command.move_deal.command import MoveDealCommand
from src.modules.crm.application.deal.command.move_deal.dto import MoveDealResultDTO
from src.modules.crm.application.deal.service.mutations import DealMutationService


class MoveDealHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: DealMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(self, command: MoveDealCommand) -> MoveDealResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.move(command)
        return MoveDealResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
