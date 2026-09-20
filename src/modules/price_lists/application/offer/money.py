from dataclasses import replace

from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.currency.application.contracts import (
    CurrencyFacade,
    conversion_payload,
    UNAVAILABLE_CONVERSION,
)


def unavailable(error_code, business_date=None):
    return dict(
        status="unavailable",
        business_date=business_date.isoformat() if business_date else None,
        purchase_price=None,
        rrp=None,
        error_code=error_code,
    )


class OfferMoneyService:
    """Consumer-owned snapshots; batch orchestration stays out of Offer domain."""

    def __init__(self, currency: CurrencyFacade, snapshots):
        self.currency, self.snapshots = currency, snapshots
        # This service lives for one publication UoW. An unconfigured import
        # remains unconfigured throughout publication, even if setup commits
        # concurrently; avoid re-reading that absence for every source batch.
        self._unconfigured = set()

    async def normalize(
        self, tenant_id, items, *, business_date=None, historical=False
    ):
        if not items:
            return []
        try:
            if historical:
                dates = await self.currency.get_business_dates(
                    tenant_id=tenant_id, timestamps=[item.observed_at for item in items]
                )
            else:
                day = business_date or await self.currency.get_business_date(
                    tenant_id=tenant_id
                )
                dates = [day] * len(items)
        except UNAVAILABLE_CONVERSION as exc:
            return [unavailable(exc.code) for _ in items]
        work, positions = [], []
        for i, (item, day) in enumerate(zip(items, dates, strict=True)):
            for kind in ("purchase_price", "rrp"):
                amount = getattr(item, kind)
                if amount is not None and item.currency:
                    positions.append((i, kind))
                    work.append((Money(amount, CurrencyCodeVO(item.currency)), day))
        converted = await self.currency.convert_many(tenant_id=tenant_id, items=work)
        results = [
            dict(
                status="converted",
                business_date=day.isoformat(),
                purchase_price=None,
                rrp=None,
                error_code=None,
            )
            for day in dates
        ]
        for (i, kind), result in zip(positions, converted, strict=True):
            if isinstance(result, UNAVAILABLE_CONVERSION):
                results[i] = unavailable(result.code, dates[i])
            elif results[i]["status"] == "converted":
                results[i][kind] = conversion_payload(result)
        return results

    async def capture(self, tenant_id, states):
        if not states:
            return
        if tenant_id in self._unconfigured:
            results = [unavailable("policy_not_configured") for _ in states]
        else:
            results = await self.normalize(tenant_id, states, historical=True)
            if all(r["error_code"] == "policy_not_configured" for r in results):
                self._unconfigured.add(tenant_id)
        await self.snapshots.add_many(
            tenant_id=tenant_id,
            records=[
                dict(state_id=state.id.uuid, **result)
                for state, result in zip(states, results, strict=True)
            ],
        )

    async def enrich(self, tenant_id, page, *, business_date=None, history=False):
        snapshots = await self.snapshots.read_many(
            tenant_id=tenant_id,
            ids=[item.id.uuid for item in page.items],
            history=history,
        )
        current = (
            []
            if history
            else await self.normalize(
                tenant_id, page.items, business_date=business_date
            )
        )
        items = []
        for i, item in enumerate(page.items):
            fields = {
                "historical_conversion": snapshots.get(
                    item.id.uuid, unavailable("legacy_state")
                )
            }
            if not history:
                fields["current_conversion"] = current[i]
            items.append(replace(item, **fields))
        return replace(page, items=items)


class ConvertedOfferService:
    def __init__(self, offers, money):
        self.offers, self.money = offers, money

    async def apply_batch(self, tenant_id, *args):
        counters, quarantined, states = await self.offers.apply_batch(tenant_id, *args)
        await self.money.capture(tenant_id, states)
        return counters, quarantined

    async def apply_missing_batch(self, tenant_id, *args):
        counters, states = await self.offers.apply_missing_batch(tenant_id, *args)
        await self.money.capture(tenant_id, states)
        return counters
