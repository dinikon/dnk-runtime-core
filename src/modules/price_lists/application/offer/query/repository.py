from typing import Protocol
from src.modules.price_lists.application.offer.dto.offer_dto import OfferPageDTO
from src.modules.price_lists.application.offer.query.list_offers_query import (
    ListOffersQuery,
)
from src.modules.price_lists.application.offer.query.offer_history_query import (
    OfferHistoryQuery,
)


class OfferQueryRepository(Protocol):
    """Порт чтения предложений и истории без сырых SQL rows."""

    async def list_offers(self, query: ListOffersQuery) -> OfferPageDTO: ...
    async def offer_history(self, query: OfferHistoryQuery) -> OfferPageDTO: ...


__all__ = ["OfferQueryRepository"]
