from collections.abc import Sequence
from datetime import date
from src.modules.price_lists.domain.offer.entity import OfferState
from src.modules.price_lists.application.offer.dto.offer_dto import (
    OfferDTO,
    OfferStateDTO,
    OfferPageDTO,
)
from src.modules.currency.application.resolution_failure.ports import (
    ResolutionFailureRecorder,
)
from src.modules.currency.application.resolution_failure.command.record_failure import (
    RecordRateResolutionFailure,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import replace
from src.modules.shared.domain.value_object.money import Money
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.time.business_calendar import BusinessCalendar
from src.modules.currency.application.facade.currency_facade import CurrencyFacade
from src.modules.currency.application.settings.reader import CurrencySettingsReader
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.currency.application.conversion.dto.unavailable_conversion import (
    UnavailableConversion,
)
from src.modules.currency.application.conversion.error import UNAVAILABLE_CONVERSION
from src.modules.price_lists.application.offer.dto.offer_conversion_dto import (
    OfferConversionDTO,
    OfferMoneySnapshotDTO,
)
from src.modules.price_lists.application.offer.ports.money_snapshot_repository import (
    OfferMoneySnapshotRepository,
)


class OfferMoneyService:
    """Date observations in the consumer and preserve consumer-owned snapshots."""

    def __init__(
        self,
        currency: CurrencyFacade,
        snapshots: OfferMoneySnapshotRepository,
        settings: CurrencySettingsReader,
        clock: ClockPort,
        display_currency: CurrencyCodeVO | None = None,
        *,
        failures: ResolutionFailureRecorder,
        operation_id: EntityIdVO,
    ):
        self.currency, self.snapshots, self.settings, self.clock = (
            currency,
            snapshots,
            settings,
            clock,
        )
        self.display_currency = display_currency
        self.failures, self.operation_id = failures, operation_id

    async def normalize(
        self,
        tenant_id: EntityIdVO,
        items: Sequence[OfferState | OfferDTO | OfferStateDTO],
        *,
        business_date: date | None = None,
        historical: bool = False,
        target: CurrencyCodeVO | None = None,
        operation_id: EntityIdVO | None = None,
    ) -> list[OfferConversionDTO]:
        if not items:
            return []
        try:
            policy = await self.settings.get(tenant_id=tenant_id)
            if historical:
                dates = [
                    BusinessCalendar.date_at(i.observed_at, policy.business_timezone)
                    for i in items
                ]
            else:
                day = business_date or BusinessCalendar.date_at(
                    self.clock.now(), policy.business_timezone
                )
                dates = [day] * len(items)
        except UNAVAILABLE_CONVERSION as exc:
            # The absence of configured timezone is itself historical information.
            for source in {CurrencyCodeVO(i.currency) for i in items if i.currency}:
                await self.failures(
                    RecordRateResolutionFailure(
                        tenant_id,
                        operation_id or self.operation_id,
                        source,
                        target,
                        business_date,
                        None,
                        0,
                        exc.code,
                    )
                )
            return [OfferConversionDTO.unavailable(exc.code) for _ in items]
        work, positions = [], []
        for i, (item, day) in enumerate(zip(items, dates, strict=True)):
            for kind in ("purchase_price", "rrp"):
                amount = getattr(item, kind)
                if amount is not None and item.currency:
                    positions.append((i, kind))
                    work.append(
                        ConversionRequest(
                            Money(amount, CurrencyCodeVO(item.currency)), day, target
                        )
                    )
        converted = await self.currency.convert_many(
            tenant_id=tenant_id, items=work, operation_id=operation_id
        )
        results = [OfferConversionDTO("converted", day) for day in dates]
        for (i, kind), result in zip(positions, converted, strict=True):
            if isinstance(result, UnavailableConversion):
                results[i] = OfferConversionDTO.unavailable(result.code, dates[i])
            elif results[i].status == "converted":
                results[i] = replace(results[i], **{kind: result})
        return results

    async def capture(
        self,
        tenant_id: EntityIdVO,
        states: Sequence[OfferState],
        *,
        operation_id: EntityIdVO,
    ) -> None:
        results = await self.normalize(
            tenant_id, states, historical=True, operation_id=operation_id
        )
        await self.snapshots.add_many(
            tenant_id=tenant_id,
            records=[
                OfferMoneySnapshotDTO(state.id, result)
                for state, result in zip(states, results, strict=True)
            ],
        )

    async def enrich(
        self,
        tenant_id: EntityIdVO,
        page: OfferPageDTO,
        *,
        business_date: date | None = None,
        history: bool = False,
    ) -> OfferPageDTO:
        snapshots = await self.snapshots.read_many(
            tenant_id=tenant_id, ids=[i.id.uuid for i in page.items], history=history
        )
        current = (
            []
            if history
            else await self.normalize(
                tenant_id, page.items, business_date=business_date
            )
        )
        display = current
        if not history and page.items:
            try:
                policy = await self.settings.get(tenant_id=tenant_id)
                today = BusinessCalendar.date_at(
                    self.clock.now(), policy.business_timezone
                )
                target = (
                    self.display_currency
                    or policy.default_display_currency
                    or await self.currency.get_functional_currency(
                        tenant_id=tenant_id, business_date=today
                    )
                )
                targets = {
                    r.purchase_price.converted.currency
                    for r in current
                    if r.purchase_price
                }
                if targets != {target}:
                    display = await self.normalize(
                        tenant_id,
                        page.items,
                        business_date=business_date,
                        target=target,
                    )
            except UNAVAILABLE_CONVERSION as exc:
                display = [OfferConversionDTO.unavailable(exc.code) for _ in page.items]
        items = []
        for i, item in enumerate(page.items):
            fields = {
                "historical_conversion": snapshots.get(
                    item.id.uuid, OfferConversionDTO.unavailable("legacy_state")
                )
            }
            if not history:
                fields.update(
                    current_conversion=current[i], display_conversion=display[i]
                )
            items.append(replace(item, **fields))
        return replace(page, items=items)


__all__ = ["OfferMoneyService"]
