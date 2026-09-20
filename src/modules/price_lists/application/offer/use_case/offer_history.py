from src.modules.price_lists.application.offer.query.offer_history_query import (
    OfferHistoryQuery,
)
from src.modules.price_lists.application.offer.query.repository import (
    OfferQueryRepository,
)


class OfferHistoryUseCase:
    """Выполняет типизированный запрос offer_history."""

    def __init__(self, repository: OfferQueryRepository):
        self.repository = repository

    async def __call__(self, query: OfferHistoryQuery):
        return await self.repository.offer_history(query)


__all__ = ["OfferHistoryUseCase"]
