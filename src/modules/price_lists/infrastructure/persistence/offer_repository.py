from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, exists, func, bindparam, String, true
from sqlalchemy.dialects.postgresql import ARRAY
from src.modules.price_lists.domain.offer.entity import Offer, OfferState
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.infrastructure.persistence.base import (
    SessionRepository,
    checked,
    identifier,
    entity_values,
)
from src.modules.price_lists.infrastructure.persistence.models import (
    PartnerOfferModel,
    PartnerOfferStateModel,
    PriceListSyncItemModel,
)


def state_entity(row):
    """Восстанавливает типизированное наблюдение из persistence."""
    return OfferState(
        identifier(row["id"], OfferStateIdVO),
        identifier(row["offer_id"], OfferIdVO),
        identifier(row["sync_run_id"], SyncRunIdVO),
        checked(row["observed_at"], datetime),
        checked(row["purchase_price"], Decimal),
        checked(row["rrp"], Decimal, optional=True),
        checked(row["currency"], str),
        checked(row["availability"], str),
        checked(row["quantity"], int, optional=True),
        checked(row["value_hash"], str),
        checked(row["change_reason"], str),
    )


def offer_entity(row):
    """Мапит результат JOIN в предложение с текущим state."""
    current = None
    if row["current_state_id"] is not None:
        current = state_entity(
            {key: row["state_" + key] for key in OfferState.__dataclass_fields__}
        )
    values = {}
    for name in Offer.__dataclass_fields__:
        if name == "current_state":
            values[name] = current
            continue
        value = row[name]
        if name == "id":
            value = identifier(value, OfferIdVO)
        elif name == "price_list_id":
            value = identifier(value, PriceListIdVO)
        elif name in ("created_by", "updated_by"):
            value = identifier(value)
        elif name.endswith("_at") or name == "missing_since":
            value = checked(value, datetime, optional=name == "missing_since")
        elif name == "consecutive_missing_runs":
            value = checked(value, int)
        else:
            value = checked(value, str)
        values[name] = value
    return Offer(**values)


class SqlAlchemyOfferRepository(SessionRepository):
    """Ограниченные выборки предложений и bulk append-only история."""

    def selection(self, offers=None):
        """Проецирует только предложение и его текущее состояние."""
        if offers is None:
            offers = PartnerOfferModel.__table__
        states = PartnerOfferStateModel.__table__
        return select(
            offers,
            *(
                states.c[name].label("state_" + name)
                for name in OfferState.__dataclass_fields__
            ),
        ).outerjoin(states, states.c.id == offers.c.current_state_id)

    async def find_many(self, tenant_id, price_list_id, external_ids):
        """Читает текущие состояния только для переданного пакета."""
        if not external_ids:
            return {}
        offers = PartnerOfferModel.__table__
        found = {}
        for start in range(0, len(external_ids), min(self.read_limit, 16000)):
            identifiers = external_ids[start : start + min(self.read_limit, 16000)]
            if self.session.bind.dialect.name == "postgresql":
                # IN(1000 keys) can scan the entire growing list before its first
                # COMMIT/ANALYZE. LATERAL LIMIT forces bounded unique-key lookups.
                keys = select(
                    func.unnest(bindparam("external_ids", type_=ARRAY(String))).label(
                        "external_id"
                    )
                ).subquery("requested")
                matched = (
                    select(offers)
                    .where(
                        offers.c.price_list_id == price_list_id.uuid,
                        offers.c.external_id == keys.c.external_id,
                    )
                    .limit(1)
                    .lateral("matched")
                )
                statement = self.selection(matched).select_from(
                    keys.join(matched, true())
                )
                result = await self.session.execute(
                    statement.execution_options(**self.execution_options(tenant_id)),
                    {"external_ids": identifiers},
                )
            else:
                result = await self.session.execute(
                    self.selection()
                    .where(
                        offers.c.price_list_id == price_list_id.uuid,
                        offers.c.external_id.in_(identifiers),
                    )
                    .execution_options(**self.execution_options(tenant_id))
                )
            for row in result.mappings():
                found[row["external_id"]] = offer_entity(row)
        return found

    async def missing_batch(self, tenant_id, price_list_id, run_id, after, limit):
        """Keyset anti-join без полного seen_ids в Python."""
        offers = PartnerOfferModel.__table__
        items = PriceListSyncItemModel.__table__
        statement = self.selection().where(
            offers.c.price_list_id == price_list_id.uuid,
            ~exists(
                select(1).where(
                    items.c.sync_run_id == run_id.uuid,
                    items.c.external_id == offers.c.external_id,
                )
            ),
        )
        if after is not None:
            statement = statement.where(offers.c.id > after.uuid)
        result = await self.session.execute(
            statement.order_by(offers.c.id)
            .limit(min(limit, self.read_limit))
            .execution_options(**self.execution_options(tenant_id))
        )
        return [offer_entity(row) for row in result.mappings()]

    async def save_batch(self, tenant_id, new, changed, states):
        """Соблюдает порядок FK: offers, states, current pointers."""

        def values(offer, *, initial=False):
            result = entity_values(offer)
            result.pop("current_state")
            result["current_state_id"] = (
                None
                if initial or offer.current_state is None
                else offer.current_state.id.uuid
            )
            return result

        await self.insert_many(
            tenant_id,
            PartnerOfferModel.__table__,
            [values(o, initial=True) for o in new],
        )
        await self.insert_many(
            tenant_id,
            PartnerOfferStateModel.__table__,
            [entity_values(state) for state in states],
        )
        await self.update_many(
            tenant_id,
            PartnerOfferModel.__table__,
            [values(o) for o in changed]
            + [
                dict(
                    id=o.id.uuid,
                    current_state_id=o.current_state.id.uuid,
                    updated_at=o.updated_at,
                )
                for o in new
            ],
        )


__all__ = ["SqlAlchemyOfferRepository", "offer_entity", "state_entity"]
