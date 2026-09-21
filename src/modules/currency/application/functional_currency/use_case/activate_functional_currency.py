from src.modules.currency.application.functional_currency.command.activate_functional_currency_command import (
    ActivateFunctionalCurrencyCommand,
)
from src.modules.currency.application.functional_currency.lifecycle import (
    FunctionalCurrencyLifecycle,
)
from src.modules.currency.domain.functional_currency.repository import (
    FunctionalCurrencyRepository,
)
from src.modules.currency.domain.policy.repository import CurrencyPolicyRepository


class ActivateFunctionalCurrencyUseCase:
    """Recheck current timezone and emit at most one activation event."""

    def __init__(
        self,
        policies: CurrencyPolicyRepository,
        periods: FunctionalCurrencyRepository,
        lifecycle: FunctionalCurrencyLifecycle,
    ):
        self.policies, self.periods, self.lifecycle = policies, periods, lifecycle

    async def __call__(self, command: ActivateFunctionalCurrencyCommand) -> None:
        await self.policies.lock(tenant_id=command.tenant_id)
        policy = await self.policies.get(tenant_id=command.tenant_id)
        period = await self.periods.get_by_id(
            tenant_id=command.tenant_id, period_id=command.period_id
        )
        await self.lifecycle.ensure(
            command.tenant_id, period, policy, period.created_by
        )


__all__ = ["ActivateFunctionalCurrencyUseCase"]
