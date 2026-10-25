from typing import Protocol
from uuid import UUID
from src.modules.crm.domain.value_object.funnel_position import FunnelPositionVO


class FunnelPort(Protocol):
    """Порт CRM для разрешения допустимой позиции процесса."""

    async def resolve(
        self, model_key: str, funnel_id: UUID | None, stage_id: UUID | None = None
    ) -> FunnelPositionVO:
        """Возвращает проверенные идентификаторы без чужой доменной модели."""
        ...
