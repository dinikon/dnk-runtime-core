from src.modules.currency.application.settings.use_case.validate_display_currency import (
    ValidateDisplayCurrencyUseCase,
)
from src.modules.currency.application.settings.query.validate_display_currency_query import (
    ValidateDisplayCurrencyQuery,
)


class CurrencyDisplayCurrencyValidator:
    """Adapt the public Currency validation scenario to Identity's port."""

    def __init__(self, use_case: ValidateDisplayCurrencyUseCase):
        self.use_case = use_case

    async def validate(self, *, tenant_id, currency) -> None:
        await self.use_case(ValidateDisplayCurrencyQuery(tenant_id, currency))


__all__ = ["CurrencyDisplayCurrencyValidator"]
