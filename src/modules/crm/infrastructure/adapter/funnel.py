from uuid import UUID
from src.modules.crm.domain.value_object.stage_snapshot import StageSnapshot
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
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

    async def describe(
        self, model_key: str, funnel_id: UUID, stage_id: UUID
    ) -> StageSnapshot:
        """Преобразует внешний Application DTO в собственный снимок CRM."""
        result = await self._service.resolve(model_key, funnel_id, stage_id)
        return StageSnapshot(
            EntityIdVO(result.funnel_id),
            EntityIdVO(result.stage_id),
            result.funnel_name,
            result.stage_name,
            result.kind,
        )

    async def lock(self, model_key: str, funnel_ids: tuple[UUID, ...]) -> None:
        """Делегирует упорядоченные блокировки публичному контракту Funnel."""
        await self._service.lock_definitions(model_key, funnel_ids)
