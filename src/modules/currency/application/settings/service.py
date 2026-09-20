from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from dataclasses import replace
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.currency.domain.repositories import (
    CurrencyDirectory,
    CurrencyPolicyRepository,
    FunctionalCurrencyRepository,
    RateRepository,
)
from src.modules.currency.application.commands import (
    InitializeCurrency,
    ConfigureCurrencyPolicy,
    SetEnabledCurrency,
    ScheduleFunctionalCurrencyChange,
    SetManualRate,
)
from datetime import timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.currency.domain.models import FunctionalCurrencyPeriod, ExchangeRate
from src.modules.currency.domain.errors import (
    CurrencyNotFound,
    CurrencyDisabled,
    CurrencyConflict,
    CurrencyPolicyNotConfigured,
    FunctionalCurrencyChangeNotAllowed,
)


class CurrencySettingsService:
    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        periods: FunctionalCurrencyRepository,
        rates: RateRepository,
        outbox,
        clock: ClockPort,
    ):
        self.directory, self.policies, self.periods, self.rates = (
            directory,
            policies,
            periods,
            rates,
        )
        self.outbox, self.clock = outbox, clock

    async def event(self, tenant_id, actor_id, name, payload, aggregate_id=None):
        await self.outbox.add(
            IntegrationEvent(
                uuid4(),
                tenant_id.uuid,
                name,
                1,
                "currency",
                aggregate_id.uuid if aggregate_id else tenant_id.uuid,
                {"actor_id": str(actor_id), **payload},
                self.clock.now(),
            )
        )

    async def validate_codes(self, codes):
        for code in set(codes):
            info = await self.directory.get(code)
            if not info.is_active:
                raise CurrencyNotFound(f"Currency {code} is not active.")

    @staticmethod
    def required_codes(policy):
        return {policy.default_transaction_currency} | (
            {policy.bridge_currency} if policy.allow_cross_rate else set()
        )

    @staticmethod
    def validate_provider(policy):
        if str(policy.provider_code) not in {"NBU", "MANUAL"}:
            raise CurrencyConflict("Provider is not registered.")

    async def initialize(self, command: InitializeCurrency):
        await self.policies.lock(tenant_id=command.tenant_id)
        try:
            await self.policies.get(tenant_id=command.tenant_id)
        except CurrencyPolicyNotConfigured:
            pass
        else:
            raise CurrencyConflict("Currency policy is already configured.")
        self.validate_provider(command.policy)
        enabled = set(command.enabled_currencies)
        required = self.required_codes(command.policy) | {command.functional_currency}
        if not required <= enabled:
            raise CurrencyDisabled("All configured currencies must be enabled.")
        await self.validate_codes(enabled | {command.policy.bridge_currency})
        now = self.clock.now()
        for code in sorted(enabled, key=str):
            await self.policies.set_enabled(
                tenant_id=command.tenant_id, code=code, enabled=True, now=now
            )
        await self.policies.save(
            tenant_id=command.tenant_id,
            policy=replace(command.policy, version=1),
            expected_version=0,
            now=now,
        )
        period = FunctionalCurrencyPeriod(
            EntityIdVO(uuid4()),
            command.functional_currency,
            command.valid_from,
            None,
            now,
            command.actor_id,
            command.reason,
        )
        await self.periods.add(tenant_id=command.tenant_id, period=period)
        await self.event(
            command.tenant_id,
            command.actor_id,
            "CurrencyPolicyChanged",
            {"version": 1, "initialized": True},
        )
        await self.event(
            command.tenant_id,
            command.actor_id,
            "FunctionalCurrencyScheduled",
            {
                "currency": str(period.currency),
                "valid_from": period.valid_from.isoformat(),
            },
            period.id,
        )

    async def configure(self, command: ConfigureCurrencyPolicy):
        await self.policies.lock(tenant_id=command.tenant_id)
        await self.policies.get(tenant_id=command.tenant_id)
        self.validate_provider(command.policy)
        required = self.required_codes(command.policy)
        await self.validate_codes(required | {command.policy.bridge_currency})
        if not required <= await self.policies.enabled(tenant_id=command.tenant_id):
            raise CurrencyDisabled("Policy currencies must be enabled first.")
        policy = replace(command.policy, version=command.expected_version + 1)
        await self.policies.save(
            tenant_id=command.tenant_id,
            policy=policy,
            expected_version=command.expected_version,
            now=self.clock.now(),
        )
        await self.event(
            command.tenant_id,
            command.actor_id,
            "CurrencyPolicyChanged",
            {"version": policy.version},
        )
        return policy

    async def set_enabled(self, command: SetEnabledCurrency):
        await self.policies.lock(tenant_id=command.tenant_id)
        policy = await self.policies.get(tenant_id=command.tenant_id)
        if command.enabled:
            await self.validate_codes([command.currency])
        else:
            await self.directory.get(command.currency)
            today = (
                self.clock.now().astimezone(ZoneInfo(policy.business_timezone)).date()
            )
            periods = await self.periods.list_periods(tenant_id=command.tenant_id)
            required = self.required_codes(policy) | {
                p.currency for p in periods if p.valid_to is None or p.valid_to >= today
            }
            if command.currency in required:
                raise CurrencyConflict(
                    "Currency is required by the policy or a current/future period."
                )
        await self.policies.set_enabled(
            tenant_id=command.tenant_id,
            code=command.currency,
            enabled=command.enabled,
            now=self.clock.now(),
        )
        await self.event(
            command.tenant_id,
            command.actor_id,
            "CurrencyEnabled" if command.enabled else "CurrencyDisabled",
            {"currency": str(command.currency)},
        )

    async def schedule(self, command: ScheduleFunctionalCurrencyChange):
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
        await self.validate_codes([command.currency])
        if command.currency not in await self.policies.enabled(
            tenant_id=command.tenant_id
        ):
            raise CurrencyDisabled("Enable the currency before scheduling it.")
        period = FunctionalCurrencyPeriod(
            EntityIdVO(uuid4()),
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
        await self.event(
            command.tenant_id,
            command.actor_id,
            "FunctionalCurrencyScheduled",
            {
                "currency": str(period.currency),
                "valid_from": period.valid_from.isoformat(),
            },
            period.id,
        )
        return period

    async def set_manual_rate(self, command: SetManualRate):
        await self.policies.lock(tenant_id=command.tenant_id)
        ExchangeRate(command.pair, command.rate)
        if command.pair.source == command.pair.target:
            raise CurrencyConflict(
                "Identity rates are internal and cannot be entered manually."
            )
        await self.validate_codes([command.pair.source, command.pair.target])
        await self.policies.get(tenant_id=command.tenant_id)
        if not {
            command.pair.source,
            command.pair.target,
        } <= await self.policies.enabled(tenant_id=command.tenant_id):
            raise CurrencyDisabled("Both currencies must be enabled.")
        record = await self.rates.set_manual(
            tenant_id=command.tenant_id,
            pair=command.pair,
            rate=command.rate,
            effective_date=command.effective_date,
            actor_id=command.actor_id,
            now=self.clock.now(),
        )
        await self.event(
            command.tenant_id,
            command.actor_id,
            "ManualExchangeRateCreated",
            {"rate_id": str(record.id), "revision": record.revision},
            record.id,
        )
        return record
