from uuid import UUID
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO
from src.modules.funnel.application.service.resolve_stage import (
    ResolveFunnelStageService,
)


class FunnelAdapter:
    """Адаптирует публичный Application-контракт Funnel для CRM."""

    def __init__(self, service: ResolveFunnelStageService) -> None:
        """Принимает сервис на той же сессии UoW."""
        self._service = service

    async def resolve(
        self, model_key: str, funnel_id: UUID | None, stage_id: UUID | None = None
    ) -> FunnelPositionVO:
        """Переводит результат в собственное значение позиции CRM."""
        result = await self._service.resolve(model_key, funnel_id, stage_id)
        return FunnelPositionVO(result.funnel_id, result.stage_id)
