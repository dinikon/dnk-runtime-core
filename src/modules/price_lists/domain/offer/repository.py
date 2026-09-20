from dataclasses import dataclass
from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.entity import Offer, OfferState


@dataclass(slots=True, frozen=True)
class MissingOfferBatch:
    """Отсутствующие предложения и курсор просмотренного диапазона."""

    items: tuple[Offer, ...]
    after_id: OfferIdVO | None


class OfferRepository(Protocol):
    """Пакетный порт предложений и append-only истории."""

    async def find_many(
        self,
        tenant_id: EntityIdVO,
        price_list_id: PriceListIdVO,
        external_ids: list[str],
    ) -> dict[str, Offer]: ...
    async def missing_batch(
        self,
        tenant_id: EntityIdVO,
        price_list_id: PriceListIdVO,
        run_id: SyncRunIdVO,
        after: OfferIdVO | None,
        limit: int,
    ) -> MissingOfferBatch: ...
    async def save_batch(
        self,
        tenant_id: EntityIdVO,
        new: list[Offer],
        changed: list[Offer],
        states: list[OfferState],
    ) -> None: ...


__all__ = ["OfferRepository", "MissingOfferBatch"]
