from collections.abc import Sequence
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.offer.entity import Offer
from src.modules.price_lists.domain.offer.value_object.values import OfferValues
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.service import OfferService
from src.modules.price_lists.application.offer.service.money import OfferMoneyService
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ConvertedOfferService:
    """Publish offer states and conversions in the same transaction."""

    def __init__(self, offers: OfferService, money: OfferMoneyService):
        self.offers, self.money = offers, money

    async def apply_batch(
        self,
        tenant_id: EntityIdVO,
        price: PriceList,
        run_id: SyncRunIdVO,
        values: Sequence[OfferValues],
        identifiers: Sequence[tuple[OfferIdVO, OfferStateIdVO]],
    ) -> tuple[dict[str, int], list[str]]:
        counters, quarantined, states = await self.offers.apply_batch(
            tenant_id, price, run_id, values, identifiers
        )
        await self.money.capture(
            tenant_id, states, operation_id=EntityIdVO(run_id.uuid)
        )
        return counters, quarantined

    async def apply_missing_batch(
        self,
        tenant_id: EntityIdVO,
        price: PriceList,
        run_id: SyncRunIdVO,
        offers: Sequence[Offer],
        state_ids: Sequence[OfferStateIdVO],
    ) -> dict[str, int]:
        counters, states = await self.offers.apply_missing_batch(
            tenant_id, price, run_id, offers, state_ids
        )
        await self.money.capture(
            tenant_id, states, operation_id=EntityIdVO(run_id.uuid)
        )
        return counters


__all__ = ["ConvertedOfferService"]
