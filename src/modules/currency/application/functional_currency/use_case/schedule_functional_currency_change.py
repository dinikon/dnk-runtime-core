from datetime import timedelta
from zoneinfo import ZoneInfo
from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.functional_currency.command.schedule_functional_currency_change_command import (
    ScheduleFunctionalCurrencyChange,
)
from src.modules.currency.application.functional_currency.dto.functional_currency_period_dto import (
    FunctionalCurrencyPeriodDTO,
)
from src.modules.currency.application.functional_currency.lifecycle import (
    FunctionalCurrencyLifecycle,
)
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyChangeNotAllowed,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.currency.domain.policy.service import CurrencyPolicyRules
from src.modules.shared.domain.time.clock_port import ClockPort


class ScheduleFunctionalCurrencyChangeUseCase:
    """Execute the schedule functional currency change transaction."""

    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        enabled_currencies: EnabledCurrencyRepository,
        periods: FunctionalCurrencyRepository,
        events: CurrencyEventWriter,
        clock: ClockPort,
        lifecycle: FunctionalCurrencyLifecycle,
    ) -> None:
        self.directory = directory
        self.policies = policies
        self.enabled_currencies = enabled_currencies
        self.periods = periods
        self.events = events
        self.clock = clock
        self.lifecycle = lifecycle
        self.rules = CurrencyPolicyRules(directory)

    async def __call__(
        self, command: ScheduleFunctionalCurrencyChange
    ) -> FunctionalCurrencyPeriodDTO:
        await self.policies.lock(tenant_id=command.tenant_id)
        policy = await self.policies.get(tenant_id=command.tenant_id)
        now = self.clock.now()
        today = now.astimezone(ZoneInfo(policy.business_timezone)).date()
        periods = await self.periods.list_periods(tenant_id=command.tenant_id)
        if (
            command.effective_from <= today
            or not periods
            or command.effective_from <= periods[-1].valid_from
        ):
            raise FunctionalCurrencyChangeNotAllowed(
                "A change must start in the future and after the last scheduled period."
            )
        if command.currency == periods[-1].currency:
            raise FunctionalCurrencyChangeNotAllowed(
                "The new currency equals the last scheduled currency."
            )
        await self.rules.validate_codes([command.currency])
        if command.currency not in await self.enabled_currencies.enabled(
            tenant_id=command.tenant_id
        ):
            raise CurrencyDisabled("Enable the currency before scheduling it.")
        period = FunctionalCurrencyPeriod(
            command.id,
            command.currency,
            command.effective_from,
            None,
            now,
            command.actor_id,
            command.reason,
        )
        periods[-1].validate_successor(period, today)
        await self.periods.close(
            tenant_id=command.tenant_id,
            period_id=periods[-1].id,
            valid_to=period.valid_from - timedelta(days=1),
        )
        await self.periods.add(tenant_id=command.tenant_id, period=period)
        await self.events.publish(
            command.tenant_id,
            command.actor_id,
            "FunctionalCurrencyScheduled",
            {
                "currency": str(period.currency),
                "valid_from": period.valid_from.isoformat(),
            },
            period.id,
        )
        await self.lifecycle.ensure(command.tenant_id, period, policy, command.actor_id)
        return FunctionalCurrencyPeriodDTO.from_entity(period)


__all__ = ["ScheduleFunctionalCurrencyChangeUseCase"]
