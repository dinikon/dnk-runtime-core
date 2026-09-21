from src.modules.currency.application.conversion.command.convert_money_batch_command import (
    ConvertMoneyBatchCommand,
)
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)
from src.modules.currency.application.conversion.dto.unavailable_conversion import (
    UnavailableConversion,
)
from src.modules.currency.application.facade.currency_facade import CurrencyFacade


class ConvertMoneyBatchUseCase:
    """Execute the convert money batch application scenario."""

    def __init__(self, facade: CurrencyFacade):
        self.facade = facade

    async def __call__(
        self, command: ConvertMoneyBatchCommand
    ) -> list[ConvertedMoney | UnavailableConversion]:
        return await self.facade.convert_many(
            tenant_id=command.tenant_id,
            items=command.requests,
            operation_id=command.operation_id,
        )


__all__ = ["ConvertMoneyBatchUseCase"]
