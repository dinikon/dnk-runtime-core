from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.functional_currency.ports import (
    ActivationScheduler,
)
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.shared.application.time.business_calendar import BusinessCalendar
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FunctionalCurrencyLifecycle:
    """Schedule or atomically acknowledge a period without changing its dates."""

    def __init__(
        self,
        periods: FunctionalCurrencyRepository,
        jobs: ActivationScheduler,
        events: CurrencyEventWriter,
        clock: ClockPort,
    ):
        self.periods, self.jobs, self.events, self.clock = periods, jobs, events, clock

    async def ensure(
        self,
        tenant_id: EntityIdVO,
        period: FunctionalCurrencyPeriod,
        policy: CurrencyPolicy,
        actor_id: EntityIdVO,
    ) -> None:
        if period.activation_emitted_at is not None:
            return
        now = self.clock.now()
        if period.valid_from <= BusinessCalendar.date_at(now, policy.business_timezone):
            if await self.periods.mark_activated(
                tenant_id=tenant_id, period_id=period.id, now=now
            ):
                await self.events.publish(
                    tenant_id,
                    actor_id,
                    "FunctionalCurrencyActivated",
                    {
                        "currency": str(period.currency),
                        "effective_date": period.valid_from.isoformat(),
                        "activated_at": now.isoformat(),
                    },
                    period.id,
                )
        else:
            await self.jobs.schedule(
                tenant_id=tenant_id,
                period_id=period.id,
                run_at=BusinessCalendar.start_of_day(
                    period.valid_from, policy.business_timezone
                ),
                policy_version=policy.version,
                now=now,
            )


__all__ = ["FunctionalCurrencyLifecycle"]
