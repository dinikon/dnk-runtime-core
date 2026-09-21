from src.modules.currency.application.events.writer import CurrencyEventWriter
from src.modules.currency.application.exchange_rate.dto.rate_record_dto import (
    RateRecordDTO,
)
from src.modules.currency.application.manual_rate.command.set_manual_rate_command import (
    SetManualRate,
)
from src.modules.currency.application.manual_rate.dto.set_manual_rate_result import (
    SetManualRateResult,
)
from src.modules.currency.domain.directory.repository import CurrencyDirectory
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.enabled_currency.repository import (
    EnabledCurrencyRepository,
)
from src.modules.currency.domain.exchange_rate.value_object.exchange_rate import (
    ExchangeRate,
)
from src.modules.currency.domain.manual_rate.repository import ManualRateRepository
from src.modules.currency.domain.policy.error import CurrencyConflict
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository
from src.modules.currency.domain.policy.service import CurrencyPolicyRules
from src.modules.shared.domain.time.clock_port import ClockPort


class SetManualRateUseCase:
    """Execute the set manual rate transaction."""

    def __init__(
        self,
        directory: CurrencyDirectory,
        policies: CurrencyPolicyRepository,
        enabled_currencies: EnabledCurrencyRepository,
        rates: ManualRateRepository,
        events: CurrencyEventWriter,
        clock: ClockPort,
    ) -> None:
        self.directory = directory
        self.policies = policies
        self.enabled_currencies = enabled_currencies
        self.rates = rates
        self.events = events
        self.clock = clock
        self.rules = CurrencyPolicyRules(directory)

    async def __call__(self, command: SetManualRate) -> SetManualRateResult:
        await self.policies.lock(tenant_id=command.tenant_id)
        ExchangeRate(command.pair, command.rate)
        if command.pair.source == command.pair.target:
            raise CurrencyConflict(
                "Identity rates are internal and cannot be entered manually."
            )
        await self.rules.validate_codes([command.pair.source, command.pair.target])
        await self.policies.get(tenant_id=command.tenant_id)
        if not {
            command.pair.source,
            command.pair.target,
        } <= await self.enabled_currencies.enabled(tenant_id=command.tenant_id):
            raise CurrencyDisabled("Both currencies must be enabled.")
        record, created = await self.rates.set_manual(
            identifier=command.id,
            tenant_id=command.tenant_id,
            pair=command.pair,
            rate=command.rate,
            effective_date=command.effective_date,
            actor_id=command.actor_id,
            now=self.clock.now(),
        )
        if not created:
            return SetManualRateResult(RateRecordDTO.from_entity(record), False)
        await self.events.publish(
            command.tenant_id,
            command.actor_id,
            "ManualExchangeRateCreated",
            {"rate_id": str(record.id), "revision": record.revision},
            record.id,
        )
        return SetManualRateResult(RateRecordDTO.from_entity(record), True)


__all__ = ["SetManualRateUseCase"]
