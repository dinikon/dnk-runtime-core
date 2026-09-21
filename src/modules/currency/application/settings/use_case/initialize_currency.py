from dataclasses import replace
from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.functional_currency.lifecycle import (
    FunctionalCurrencyLifecycle,
)
from src.modules.currency.application.provider.catalog import RateSourceCatalog
from src.modules.currency.application.settings.command.initialize_currency_command import (
    InitializeCurrency,
)
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.error import CurrencyConflict
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.currency.domain.policy.service import CurrencyPolicyRules
from src.modules.shared.domain.time.clock_port import ClockPort


class InitializeCurrencyUseCase:
    """Execute the initialize currency transaction."""

    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        enabled_currencies: EnabledCurrencyRepository,
        periods: FunctionalCurrencyRepository,
        events: CurrencyEventWriter,
        clock: ClockPort,
        sources: RateSourceCatalog,
        lifecycle: FunctionalCurrencyLifecycle,
    ) -> None:
        self.directory = directory
        self.policies = policies
        self.enabled_currencies = enabled_currencies
        self.periods = periods
        self.events = events
        self.clock = clock
        self.sources = sources
        self.lifecycle = lifecycle
        self.rules = CurrencyPolicyRules(directory)

    async def __call__(self, command: InitializeCurrency):
        await self.policies.lock(tenant_id=command.tenant_id)
        try:
            await self.policies.get(tenant_id=command.tenant_id)
        except CurrencyPolicyNotConfigured:
            pass
        else:
            raise CurrencyConflict("Currency policy is already configured.")
        self.sources.require(command.policy.provider_code)
        enabled = set(command.enabled_currencies)
        required = self.rules.required_codes(command.policy) | {
            command.functional_currency
        }
        if not required <= enabled:
            raise CurrencyDisabled("All configured currencies must be enabled.")
        await self.rules.validate_codes(enabled | {command.policy.bridge_currency})
        now = self.clock.now()
        for code in sorted(enabled, key=str):
            await self.enabled_currencies.set_enabled(
                tenant_id=command.tenant_id, code=code, enabled=True, now=now
            )
            await self.events.publish(
                command.tenant_id,
                command.actor_id,
                "CurrencyEnabled",
                {"currency": str(code)},
            )
        await self.policies.save(
            tenant_id=command.tenant_id,
            policy=replace(command.policy, version=1),
            expected_version=0,
            now=now,
        )
        period = FunctionalCurrencyPeriod(
            command.id,
            command.functional_currency,
            command.valid_from,
            None,
            now,
            command.actor_id,
            command.reason,
        )
        await self.periods.add(tenant_id=command.tenant_id, period=period)
        await self.events.publish(
            command.tenant_id,
            command.actor_id,
            "CurrencyPolicyChanged",
            {"version": 1, "initialized": True},
        )
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
        await self.lifecycle.ensure(
            command.tenant_id, period, command.policy, command.actor_id
        )


__all__ = ["InitializeCurrencyUseCase"]
