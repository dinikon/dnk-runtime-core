from src.modules.crm.application.lead.command.move_lead.command import MoveLeadCommand
from src.modules.crm.application.lead.command.move_lead.dto import MoveLeadResultDTO
from src.modules.crm.application.lead.service.mutations import LeadMutationService


class MoveLeadHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: LeadMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(self, command: MoveLeadCommand) -> MoveLeadResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.move(command)
        return MoveLeadResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
