from src.modules.currency.application.enabled_currency.command.enable_currency_command import (
    EnableCurrencyCommand,
)
from src.modules.currency.application.enabled_currency.command.set_enabled_currency_command import (
    SetEnabledCurrency,
)
from src.modules.currency.application.enabled_currency.use_case.set_enabled_currency import (
    SetEnabledCurrencyUseCase,
)


class EnableCurrencyUseCase:
    """Enable a currency for new tenant operations."""

    def __init__(self, change: SetEnabledCurrencyUseCase):
        self.change = change

    async def __call__(self, command: EnableCurrencyCommand) -> None:
        await self.change(
            SetEnabledCurrency(
                command.tenant_id, command.actor_id, command.currency, True
            )
        )


__all__ = ["EnableCurrencyUseCase"]
