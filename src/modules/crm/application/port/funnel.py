from typing import Protocol
from uuid import UUID
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO
from src.modules.crm.domain.value_object.stage_snapshot import StageSnapshot


class FunnelPort(Protocol):
    """Порт CRM для разрешения допустимой позиции процесса."""

    async def resolve(
        self, model_key: str, funnel_id: UUID | None, stage_id: UUID | None = None
    ) -> FunnelPositionVO:
        """Возвращает проверенные идентификаторы без чужой доменной модели."""
        ...

    async def describe(
        self, model_key: str, funnel_id: UUID, stage_id: UUID
    ) -> StageSnapshot:
        """Возвращает собственный снимок CRM для истории."""
        ...

    async def lock(self, model_key: str, funnel_ids: tuple[UUID, ...]) -> None:
        """Блокирует определения до блокировки карточек."""
        ...
