from collections.abc import Sequence
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.entity import PriceList
from src.modules.price_lists.domain.offer.entity import Offer
from src.modules.price_lists.domain.offer.value_object.values import OfferValues
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from typing import Protocol


class OfferPublication(Protocol):
    """Apply offer observations and their snapshots in the publication UoW."""

    async def apply_batch(
        self,
        tenant_id: EntityIdVO,
        price: PriceList,
        run_id: SyncRunIdVO,
        values: Sequence[OfferValues],
        identifiers: Sequence[tuple[OfferIdVO, OfferStateIdVO]],
    ) -> tuple[dict[str, int], list[str]]: ...
    async def apply_missing_batch(
        self,
        tenant_id: EntityIdVO,
        price: PriceList,
        run_id: SyncRunIdVO,
        offers: Sequence[Offer],
        state_ids: Sequence[OfferStateIdVO],
    ) -> dict[str, int]: ...


__all__ = ["OfferPublication"]
