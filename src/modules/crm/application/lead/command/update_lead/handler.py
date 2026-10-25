from src.modules.crm.application.lead.command.update_lead.command import (
    UpdateLeadCommand,
)
from src.modules.crm.application.lead.command.update_lead.dto import UpdateLeadResultDTO
from src.modules.crm.application.lead.service.mutations import LeadMutationService


class UpdateLeadHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: LeadMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(self, command: UpdateLeadCommand) -> UpdateLeadResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.update(command)
        return UpdateLeadResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
