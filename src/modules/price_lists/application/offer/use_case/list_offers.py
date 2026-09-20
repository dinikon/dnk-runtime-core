from src.modules.price_lists.application.offer.query.list_offers_query import (
    ListOffersQuery,
)
from src.modules.price_lists.application.offer.query.repository import (
    OfferQueryRepository,
)


class ListOffersUseCase:
    """Выполняет типизированный запрос list_offers."""

    def __init__(self, repository: OfferQueryRepository, money):
        self.repository = repository
        self.money = money

    async def __call__(self, query: ListOffersQuery):
        """Выполняет сценарий через внедрённые доменные порты."""
        page = await self.repository.list_offers(query)
        return await self.money.enrich(
            query.tenant_id, page, business_date=query.business_date
        )


__all__ = ["ListOffersUseCase"]
