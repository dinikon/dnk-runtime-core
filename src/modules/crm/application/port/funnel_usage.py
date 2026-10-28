from typing import Protocol
from uuid import UUID


class FunnelUsageQueryPort(Protocol):
    """Чтение количества карточек без загрузки агрегатов."""

    async def counts(self, model_key: str, funnel_id: UUID) -> dict[UUID, int]:
        """Возвращает количества всех карточек, включая конвертированные лиды."""
        ...
