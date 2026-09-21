from dataclasses import replace
from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.functional_currency.lifecycle import (
    FunctionalCurrencyLifecycle,
)
from src.modules.currency.application.policy.command.configure_currency_policy_command import (
    ConfigureCurrencyPolicy,
)
from src.modules.currency.application.policy.dto.currency_policy_dto import (
    CurrencyPolicyDTO,
)
from src.modules.currency.application.provider.catalog import RateSourceCatalog
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


class ConfigureCurrencyPolicyUseCase:
    """Execute the configure currency policy transaction."""

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

    async def __call__(self, command: ConfigureCurrencyPolicy) -> CurrencyPolicyDTO:
        await self.policies.lock(tenant_id=command.tenant_id)
        current = await self.policies.get(tenant_id=command.tenant_id)
        if current.version != command.expected_version:
            raise CurrencyConflict("Currency settings changed. Reload before saving.")
        if replace(command.policy, version=current.version) == current:
            return CurrencyPolicyDTO.from_entity(current)
        self.sources.require(command.policy.provider_code)
        required = self.rules.required_codes(command.policy)
        await self.rules.validate_codes(required | {command.policy.bridge_currency})
        if not required <= await self.enabled_currencies.enabled(
            tenant_id=command.tenant_id
        ):
            raise CurrencyDisabled("Policy currencies must be enabled first.")
        policy = replace(command.policy, version=command.expected_version + 1)
        await self.policies.save(
            tenant_id=command.tenant_id,
            policy=policy,
            expected_version=command.expected_version,
            now=self.clock.now(),
        )
        await self.events.publish(
            command.tenant_id,
            command.actor_id,
            "CurrencyPolicyChanged",
            {"version": policy.version},
        )
        if current.business_timezone != policy.business_timezone:
            for period in await self.periods.list_periods(tenant_id=command.tenant_id):
                await self.lifecycle.ensure(
                    command.tenant_id, period, policy, command.actor_id
                )
        return CurrencyPolicyDTO.from_entity(policy)


__all__ = ["ConfigureCurrencyPolicyUseCase"]
