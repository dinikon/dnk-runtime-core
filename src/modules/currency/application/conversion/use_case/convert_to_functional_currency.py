from src.modules.currency.application.conversion.command.convert_money_command import (
    ConvertMoneyCommand,
)
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)
from src.modules.currency.application.facade.currency_facade import CurrencyFacade


class ConvertToFunctionalCurrencyUseCase:
    """Execute the convert to functional currency application scenario."""

    def __init__(self, facade: CurrencyFacade):
        self.facade = facade

    async def __call__(self, command: ConvertMoneyCommand) -> ConvertedMoney:
        r = command.request
        return await self.facade.convert_to_functional(
            tenant_id=command.tenant_id,
            money=r.money,
            business_date=r.business_date,
            purpose=r.purpose,
            precision=r.precision,
        )


__all__ = ["ConvertToFunctionalCurrencyUseCase"]
