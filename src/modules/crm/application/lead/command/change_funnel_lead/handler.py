from src.modules.crm.application.lead.command.change_funnel_lead.command import (
    ChangeLeadFunnelCommand,
)
from src.modules.crm.application.lead.command.change_funnel_lead.dto import (
    ChangeLeadFunnelResultDTO,
)
from src.modules.crm.application.lead.service.mutations import LeadMutationService


class ChangeLeadFunnelHandler:
    """Координирует отдельный сценарий через общий Application service."""

    def __init__(self, service: LeadMutationService) -> None:
        """Принимает сервис без инфраструктурных типов."""
        self._service = service

    async def execute(
        self, command: ChangeLeadFunnelCommand
    ) -> ChangeLeadFunnelResultDTO:
        """Возвращает собственный результат сценария без commit."""
        entity, mapping = await self._service.change_funnel(command)
        return ChangeLeadFunnelResultDTO(
            entity.id.uuid,
            entity.position.funnel_id.uuid,
            entity.position.stage_id.uuid,
            entity.position.revision,
            mapping,
        )
