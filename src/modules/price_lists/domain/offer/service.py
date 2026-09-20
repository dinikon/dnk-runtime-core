from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.price_lists.domain.offer.entity import Offer
from src.modules.price_lists.domain.offer.repository import OfferRepository


class OfferService:
    """Координирует сохранение проверенных предложений и истории."""

    def __init__(self, repository: OfferRepository, clock: ClockPort):
        self.repository = repository
        self.clock = clock

    async def apply_batch(self, tenant_id, price, run_id, values, identifiers):
        """Применяет new/reappeared policy к одному ограниченному пакету."""
        now = self.clock.now()
        existing = await self.repository.find_many(
            tenant_id, price.id, [v.external_id for v in values]
        )
        new = []
        changed = []
        states = []
        quarantine = []
        counters = dict(
            created=0, changed=0, unchanged=0, reappeared=0, ignored=0, quarantined=0
        )
        for value, (offer_id, state_id) in zip(values, identifiers, strict=True):
            offer = existing.get(value.external_id)
            if offer is None:
                if price.new_item_policy in ("quarantine", "ignore"):
                    counters[
                        (
                            "quarantined"
                            if price.new_item_policy == "quarantine"
                            else "ignored"
                        )
                    ] += 1
                    if price.new_item_policy == "quarantine":
                        quarantine.append(value.external_id)
                    continue
                offer = Offer.create(offer_id, price.id, value, price.updated_by, now)
                new.append(offer)
                counters["created"] += 1
            else:
                if (
                    offer.lifecycle_status in ("missing", "archived")
                    or offer.missing_since
                ):
                    counters["reappeared"] += 1
                changed.append(offer)
            state = offer.observe(value, state_id, run_id, price.updated_by, now)
            if state:
                states.append(state)
                counters["changed"] += 1
            else:
                counters["unchanged"] += 1
        await self.repository.save_batch(tenant_id, new, changed, states)
        return counters, quarantine

    async def apply_missing_batch(self, tenant_id, price, run_id, offers, state_ids):
        """Применяет отсутствие без полного набора ID в памяти."""
        states = []
        counters = dict(missing=0, changed=0)
        now = self.clock.now()
        for offer, state_id in zip(offers, state_ids, strict=True):
            state = offer.mark_missing(
                price.missing_item_policy,
                price.missing_threshold,
                state_id,
                run_id,
                price.updated_by,
                now,
            )
            if offer.consecutive_missing_runs >= price.missing_threshold:
                counters["missing"] += 1
            if state:
                states.append(state)
                counters["changed"] += 1
        await self.repository.save_batch(tenant_id, [], offers, states)
        return counters


__all__ = ["OfferService"]
