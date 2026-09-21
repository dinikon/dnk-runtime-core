from zoneinfo import ZoneInfo
from src.modules.currency.application.enabled_currency.command.set_enabled_currency_command import (
    SetEnabledCurrency,
)
from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.error import CurrencyConflict
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.currency.domain.policy.service import CurrencyPolicyRules
from src.modules.shared.domain.time.clock_port import ClockPort


class SetEnabledCurrencyUseCase:
    """Execute the set enabled currency transaction."""

    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        enabled_currencies: EnabledCurrencyRepository,
        periods: FunctionalCurrencyRepository,
        events: CurrencyEventWriter,
        clock: ClockPort,
    ) -> None:
        self.directory = directory
        self.policies = policies
        self.enabled_currencies = enabled_currencies
        self.periods = periods
        self.events = events
        self.clock = clock
        self.rules = CurrencyPolicyRules(directory)

    async def __call__(self, command: SetEnabledCurrency):
        await self.policies.lock(tenant_id=command.tenant_id)
        policy = await self.policies.get(tenant_id=command.tenant_id)
        if command.enabled:
            await self.rules.validate_codes([command.currency])
        else:
            await self.directory.get(command.currency)
            today = (
                self.clock.now().astimezone(ZoneInfo(policy.business_timezone)).date()
            )
            periods = await self.periods.list_periods(tenant_id=command.tenant_id)
            required = self.rules.required_codes(policy) | {
                p.currency for p in periods if p.valid_to is None or p.valid_to >= today
            }
            if command.currency in required:
                raise CurrencyConflict(
                    "Currency is required by the policy or a current/future period."
                )
        enabled = await self.enabled_currencies.enabled(tenant_id=command.tenant_id)
        if (command.currency in enabled) == command.enabled:
            return
        await self.enabled_currencies.set_enabled(
            tenant_id=command.tenant_id,
            code=command.currency,
            enabled=command.enabled,
            now=self.clock.now(),
        )
        await self.events.publish(
            command.tenant_id,
            command.actor_id,
            "CurrencyEnabled" if command.enabled else "CurrencyDisabled",
            {"currency": str(command.currency)},
        )


__all__ = ["SetEnabledCurrencyUseCase"]
