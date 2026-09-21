from src.modules.currency.application.conversion.command.convert_money_command import (
    ConvertMoneyCommand,
)
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)
from src.modules.currency.application.facade.currency_facade import CurrencyFacade
from src.modules.currency.domain.exchange_rate.error import InvalidExchangeRate


class ConvertMoneyUseCase:
    """Execute the convert money application scenario."""

    def __init__(self, facade: CurrencyFacade):
        self.facade = facade

    async def __call__(self, command: ConvertMoneyCommand) -> ConvertedMoney:
        r = command.request
        if r.target is None:
            raise InvalidExchangeRate("A target currency is required.")
        return await self.facade.convert(
            tenant_id=command.tenant_id,
            money=r.money,
            target=r.target,
            date=r.business_date,
            purpose=r.purpose,
            precision=r.precision,
        )


__all__ = ["ConvertMoneyUseCase"]
