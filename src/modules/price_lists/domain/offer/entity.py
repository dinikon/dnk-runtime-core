from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.value_object.values import OfferValues
from src.modules.price_lists.domain.offer.value_object.state_hash import (
    canonical_state_hash,
)


@dataclass(slots=True)
class OfferState:
    """Историческое наблюдение цены и наличия предложения."""

    id: OfferStateIdVO
    offer_id: OfferIdVO
    sync_run_id: SyncRunIdVO
    observed_at: datetime
    purchase_price: Decimal
    rrp: Decimal | None
    currency: str
    availability: str
    quantity: int | None
    value_hash: str
    change_reason: str

    def matches(self, values: OfferValues) -> bool:
        """Сравнивает значения без зависимости от старой версии хеша."""
        return (
            canonical_state_hash(
                purchase_price=self.purchase_price,
                rrp=self.rrp,
                currency=self.currency,
                availability=self.availability,
                quantity=self.quantity,
            )
            == values.value_hash
        )


@dataclass(slots=True)
class Offer:
    """Предложение партнёра с текущим состоянием и missing policy."""

    id: OfferIdVO
    price_list_id: PriceListIdVO
    external_id: str
    sku: str
    title: str
    lifecycle_status: str
    first_seen_at: datetime
    last_seen_at: datetime
    missing_since: datetime | None
    consecutive_missing_runs: int
    created_by: EntityIdVO
    updated_by: EntityIdVO
    created_at: datetime
    updated_at: datetime
    current_state: OfferState | None = None

    @classmethod
    def create(cls, offer_id, price_list_id, values: OfferValues, actor_id, now):
        """Создаёт предложение с едиными audit timestamps."""
        return cls(
            offer_id,
            price_list_id,
            values.external_id,
            values.sku,
            values.title,
            "active",
            now,
            now,
            None,
            0,
            actor_id,
            actor_id,
            now,
            now,
        )

    def observe(
        self, values: OfferValues, state_id, run_id, actor_id, now
    ) -> OfferState | None:
        """Применяет наблюдение и создаёт историю только при изменении."""
        reason = (
            "initial"
            if self.current_state is None
            else (
                "reappeared"
                if self.lifecycle_status in ("missing", "archived")
                or self.missing_since
                else "source_change"
            )
        )
        changed = any(
            (
                self.sku != values.sku,
                self.title != values.title,
                self.lifecycle_status != "active",
                self.missing_since is not None,
                self.consecutive_missing_runs != 0,
                self.last_seen_at != now,
            )
        )
        self.sku = values.sku
        self.title = values.title
        self.lifecycle_status = "active"
        self.last_seen_at = now
        self.missing_since = None
        self.consecutive_missing_runs = 0
        if changed:
            self.updated_by = actor_id
            self.updated_at = now
        if self.current_state is not None and self.current_state.matches(values):
            return None
        state = OfferState(
            state_id,
            self.id,
            run_id,
            now,
            values.purchase_price,
            values.rrp,
            values.currency,
            values.availability,
            values.quantity,
            values.value_hash,
            reason,
        )
        self.current_state = state
        self.updated_by = actor_id
        self.updated_at = now
        return state

    def mark_missing(
        self, policy: str, threshold: int, state_id, run_id, actor_id, now
    ) -> OfferState | None:
        """Учитывает отсутствие в полностью валидном прайсе."""
        self.consecutive_missing_runs += 1
        self.missing_since = self.missing_since or now
        self.updated_by = actor_id
        self.updated_at = now
        if self.consecutive_missing_runs < threshold:
            return None
        if policy in ("mark_missing", "archive"):
            self.lifecycle_status = (
                "missing" if policy == "mark_missing" else "archived"
            )
        if policy != "mark_out_of_stock" or self.current_state is None:
            return None
        current = self.current_state
        values = OfferValues(
            self.external_id,
            self.sku,
            self.title,
            current.purchase_price,
            current.rrp,
            current.currency,
            "out_of_stock",
            0,
        )
        self.lifecycle_status = "active"
        if current.matches(values):
            return None
        state = OfferState(
            state_id,
            self.id,
            run_id,
            now,
            values.purchase_price,
            values.rrp,
            values.currency,
            values.availability,
            values.quantity,
            values.value_hash,
            "missing_policy",
        )
        self.current_state = state
        return state


__all__ = ["Offer", "OfferState"]
