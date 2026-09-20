from src.modules.price_lists.application.offer.query.list_offers_query import (
    ListOffersQuery,
)
from src.modules.price_lists.application.offer.query.repository import (
    OfferQueryRepository,
)


class ListOffersUseCase:
    """Выполняет типизированный запрос list_offers."""

    def __init__(self, repository: OfferQueryRepository):
        self.repository = repository

    async def __call__(self, query: ListOffersQuery):
        """Выполняет сценарий через внедрённые доменные порты."""
        return await self.repository.list_offers(query)


__all__ = ["ListOffersUseCase"]
