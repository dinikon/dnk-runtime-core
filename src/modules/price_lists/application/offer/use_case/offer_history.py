from src.modules.price_lists.application.offer.query.offer_history_query import (
    OfferHistoryQuery,
)
from src.modules.price_lists.application.offer.query.repository import (
    OfferQueryRepository,
)


class OfferHistoryUseCase:
    """Выполняет типизированный запрос offer_history."""

    def __init__(self, repository: OfferQueryRepository, money):
        self.repository = repository
        self.money = money

    async def __call__(self, query: OfferHistoryQuery):
        """Выполняет сценарий через внедрённые доменные порты."""
        page = await self.repository.offer_history(query)
        return await self.money.enrich(query.tenant_id, page, history=True)


__all__ = ["OfferHistoryUseCase"]
