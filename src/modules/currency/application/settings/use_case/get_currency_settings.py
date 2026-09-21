from zoneinfo import ZoneInfo
from src.modules.currency.application.functional_currency.dto.functional_currency_period_dto import (
    FunctionalCurrencyPeriodDTO,
)
from src.modules.currency.application.policy.dto.currency_policy_dto import (
    CurrencyPolicyDTO,
)
from src.modules.currency.application.provider.query.repository import (
    ProviderStatusQueryRepository,
)
from src.modules.currency.application.settings.dto.currency_settings_dto import (
    CurrencySettingsDTO,
)
from src.modules.currency.application.settings.query.get_currency_settings_query import (
    GetCurrencySettingsQuery,
)
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.application.time.business_calendar import BusinessCalendar
from src.modules.shared.domain.time.clock_port import ClockPort


class GetCurrencySettingsUseCase:
    """Read policy, permissions data, periods and the next business-day boundary."""

    def __init__(
        self,
        policies: CurrencyPolicyRepository,
        periods: FunctionalCurrencyRepository,
        rates: ProviderStatusQueryRepository,
        clock: ClockPort,
        enabled_currencies: EnabledCurrencyRepository,
    ):
        self.policies, self.periods, self.rates, self.clock = (
            policies,
            periods,
            rates,
            clock,
        )
        self.enabled_currencies = enabled_currencies

    async def __call__(self, query: GetCurrencySettingsQuery) -> CurrencySettingsDTO:
        try:
            policy = await self.policies.get(tenant_id=query.tenant_id)
        except CurrencyPolicyNotConfigured:
            policy = None
        # A presentation default is never persisted as an organization's policy.
        now = self.clock.now()
        today = now.astimezone(
            ZoneInfo(policy.business_timezone if policy else "Europe/Kyiv")
        ).date()
        periods = tuple(await self.periods.list_periods(tenant_id=query.tenant_id))
        enabled = tuple(
            sorted(
                await self.enabled_currencies.enabled(tenant_id=query.tenant_id),
                key=str,
            )
        )
        return CurrencySettingsDTO(
            policy is not None,
            CurrencyPolicyDTO.from_entity(policy) if policy else None,
            enabled,
            tuple(FunctionalCurrencyPeriodDTO.from_entity(p) for p in periods),
            next((p.currency for p in periods if p.contains(today)), None),
            next((p.currency for p in periods if p.valid_from > today), None),
            today,
            await self.rates.provider_status(ProviderCode("NBU")),
            (
                (
                    policy.default_display_currency
                    or next((p.currency for p in periods if p.contains(today)), None)
                )
                if policy
                else None
            ),
            BusinessCalendar.next_day(
                now, policy.business_timezone if policy else "Europe/Kyiv"
            ),
        )


__all__ = ["GetCurrencySettingsUseCase"]
