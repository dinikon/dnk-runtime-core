from zoneinfo import ZoneInfo

from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.currency.domain.models import ProviderCode
from src.modules.currency.domain.errors import CurrencyPolicyNotConfigured
from src.modules.currency.domain.repositories import (
    CurrencyPolicyRepository,
    FunctionalCurrencyRepository,
    RateRepository,
)
from ..query.get_currency_settings_query import GetCurrencySettingsQuery
from ..dto.currency_settings_dto import CurrencySettingsDTO


class GetCurrencySettingsUseCase:
    def __init__(
        self,
        policies: CurrencyPolicyRepository,
        periods: FunctionalCurrencyRepository,
        rates: RateRepository,
        clock: ClockPort,
    ):
        self.policies, self.periods, self.rates, self.clock = (
            policies,
            periods,
            rates,
            clock,
        )

    async def __call__(self, query: GetCurrencySettingsQuery) -> CurrencySettingsDTO:
        try:
            policy = await self.policies.get(tenant_id=query.tenant_id)
        except CurrencyPolicyNotConfigured:
            policy = None
        # A presentation default is never persisted as an organization's policy.
        today = (
            self.clock.now()
            .astimezone(ZoneInfo(policy.business_timezone if policy else "Europe/Kyiv"))
            .date()
        )
        periods = tuple(await self.periods.list_periods(tenant_id=query.tenant_id))
        enabled = tuple(
            sorted(await self.policies.enabled(tenant_id=query.tenant_id), key=str)
        )
        return CurrencySettingsDTO(
            policy is not None,
            policy,
            enabled,
            periods,
            next((p.currency for p in periods if p.contains(today)), None),
            next((p.currency for p in periods if p.valid_from > today), None),
            today,
            await self.rates.provider_status(ProviderCode("NBU")),
        )
