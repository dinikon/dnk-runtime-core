from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.crm.domain.value_object.stage_snapshot import StageSnapshot
from src.modules.crm.domain.lead.repository import LeadRepositoryProtocol
from src.modules.crm.domain.deal.repository import DealRepositoryProtocol
from src.modules.crm.application.port.funnel_usage import FunnelUsageQueryPort
from src.modules.crm.application.port.position_history import (
    PositionHistoryPort,
    PositionHistoryEntry,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class RelocateFunnelStageDTO:
    """Входной снимок публичного Application-контракта CRM."""

    funnel_id: UUID
    stage_id: UUID
    funnel_name: str
    stage_name: str
    kind: str


@dataclass(frozen=True, slots=True)
class RelocateFunnelCardsResultDTO:
    """Число системно перенесённых карточек."""

    moved_cards_count: int


class FunnelCardsService:
    """Публичный Application-контракт CRM для использования определения Funnel."""

    def __init__(
        self,
        leads: LeadRepositoryProtocol,
        deals: DealRepositoryProtocol,
        usage: FunnelUsageQueryPort,
        history: PositionHistoryPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты одной транзакции; определения уже заблокированы снаружи."""
        self._leads = leads
        self._deals = deals
        self._usage = usage
        self._history = history
        self._uuid = uuid

    async def counts(self, model_key: str, funnel_id: UUID) -> dict[UUID, int]:
        """Читает количества без изменения карточек."""
        return await self._usage.counts(model_key, funnel_id)

    async def relocate(
        self,
        *,
        model_key: str,
        removed: tuple[RelocateFunnelStageDTO, ...],
        target: RelocateFunnelStageDTO,
        actor_id: UUID,
        now: datetime,
    ) -> RelocateFunnelCardsResultDTO:
        """Переносит агрегаты и сохраняет факты в уже открытом UoW."""
        repository = self._leads if model_key == "crm.lead" else self._deals
        previous_by_id = {
            EntityIdVO(stage.stage_id): self._snapshot(stage) for stage in removed
        }
        current = self._snapshot(target)
        entities = await repository.list_in_stages_for_update(
            current.funnel_id, tuple(previous_by_id)
        )
        for entity in entities:
            previous = entity.position
            entity.relocate_after_stage_deletion(
                funnel_id=current.funnel_id,
                stage_id=current.stage_id,
                actor_id=EntityIdVO(actor_id),
                now=now,
            )
            await repository.save(entity)
            await self._history.append(
                PositionHistoryEntry(
                    self._uuid.new(),
                    model_key,
                    entity.id.uuid,
                    previous_by_id[previous.stage_id],
                    current,
                    previous.revision,
                    entity.position.revision,
                    "stage_deleted",
                    actor_id,
                    now,
                )
            )
        return RelocateFunnelCardsResultDTO(len(entities))

    @staticmethod
    def _snapshot(value: RelocateFunnelStageDTO) -> StageSnapshot:
        """Преобразует Application-вход в собственный снимок Domain CRM."""
        return StageSnapshot(
            EntityIdVO(value.funnel_id),
            EntityIdVO(value.stage_id),
            value.funnel_name,
            value.stage_name,
            value.kind,
        )
