from dataclasses import asdict
from src.modules.funnel.application.port.cards import FunnelCardsPort
from src.modules.funnel.application.query.get_funnel.dto import GetFunnelStageDTO
from src.modules.funnel.application.query.get_funnel.query import GetFunnelQuery
from src.modules.funnel.application.query.get_funnel.dto import GetFunnelResultDTO
from src.modules.funnel.application.port.query_repository import (
    FunnelQueryRepositoryProtocol,
)
from src.modules.funnel.domain.error import FunnelNotFoundError, FunnelError


class GetFunnelHandler:
    """Читает конкретную проекцию без восстановления Domain."""

    def __init__(
        self, repository: FunnelQueryRepositoryProtocol, cards: FunnelCardsPort
    ) -> None:
        """Принимает порт чтения."""
        self._repository = repository
        self._cards = cards

    async def execute(self, query: GetFunnelQuery) -> GetFunnelResultDTO:
        """Возвращает типизированный результат чтения."""
        row = await self._repository.get(query.funnel_id)
        if row is None:
            raise FunnelNotFoundError("Воронка не найдена.")
        counts = await self._cards.counts(row.model_key, row.id)
        return GetFunnelResultDTO(
            row.id,
            row.model_key,
            row.name,
            row.is_default,
            row.revision,
            tuple(
                GetFunnelStageDTO(**asdict(stage), cards_count=counts.get(stage.id, 0))
                for stage in row.stages
            ),
            row.created_at,
            row.updated_at,
        )
