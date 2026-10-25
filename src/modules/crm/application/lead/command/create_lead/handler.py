from src.modules.crm.application.lead.command.create_lead.command import (
    CreateLeadCommand,
)
from src.modules.crm.application.lead.command.create_lead.dto import CreateLeadResultDTO
from src.modules.crm.application.lead.service.mutations import LeadMutationService


class CreateLeadHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: LeadMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(self, command: CreateLeadCommand) -> CreateLeadResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.create(command)
        return CreateLeadResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
