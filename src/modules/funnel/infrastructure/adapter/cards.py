from datetime import datetime
from uuid import UUID
from src.modules.funnel.application.port.cards import FunnelStageSnapshotDTO
from src.modules.crm.application.service.funnel_cards import (
    FunnelCardsService,
    RelocateFunnelStageDTO,
)


class CrmFunnelCardsAdapter:
    """Адаптирует публичный Application-контракт владельца карточек."""

    def __init__(self, service: FunnelCardsService) -> None:
        """Принимает сервис на той же сессии UoW."""
        self._service = service

    @staticmethod
    def _snapshot(value: FunnelStageSnapshotDTO) -> RelocateFunnelStageDTO:
        """Преобразует снимок в тип публичного контракта CRM."""
        return RelocateFunnelStageDTO(
            value.funnel_id,
            value.stage_id,
            value.funnel_name,
            value.stage_name,
            value.kind,
        )

    async def counts(self, model_key: str, funnel_id: UUID) -> dict[UUID, int]:
        """Делегирует чтение владельцу карточек."""
        return await self._service.counts(model_key, funnel_id)

    async def relocate(
        self,
        *,
        model_key: str,
        removed: tuple[FunnelStageSnapshotDTO, ...],
        target: FunnelStageSnapshotDTO,
        actor_id: UUID,
        now: datetime,
    ) -> int:
        """Не раскрывает чужие агрегаты за границей адаптера."""
        result = await self._service.relocate(
            model_key=model_key,
            removed=tuple(self._snapshot(value) for value in removed),
            target=self._snapshot(target),
            actor_id=actor_id,
            now=now,
        )
        return result.moved_cards_count
