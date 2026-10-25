from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import dataclass
from uuid import UUID
from src.modules.funnel.domain.repository import FunnelRepositoryProtocol
from src.modules.funnel.domain.error import FunnelNotFoundError


@dataclass(frozen=True, slots=True)
class ResolvedFunnelStageDTO:
    """Проверенные идентификаторы для domain-решения потребителя."""

    funnel_id: UUID
    stage_id: UUID
    definition_revision: int


class ResolveFunnelStageService:
    """Публичный Application-контракт разрешения назначения."""

    def __init__(self, repository: FunnelRepositoryProtocol) -> None:
        """Принимает порт определения процесса."""
        self._repository = repository

    async def resolve(
        self, model_key: str, funnel_id: UUID | None, stage_id: UUID | None = None
    ) -> ResolvedFunnelStageDTO:
        """Загружает агрегат для проверки типа и стадии, без скрытого создания."""
        entity = (
            await self._repository.get(EntityIdVO(funnel_id))
            if funnel_id
            else await self._repository.get_default(model_key)
        )
        if entity is None:
            raise FunnelNotFoundError(
                "Нет доступной воронки. Проверьте миграции tenant."
            )
        stage = entity.select_stage(
            model_key, EntityIdVO(stage_id) if stage_id else None
        )
        return ResolvedFunnelStageDTO(entity.id.uuid, stage.id.uuid, entity.revision)
