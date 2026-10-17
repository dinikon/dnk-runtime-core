from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO


class ReferenceDataProfileCurrencyValidator:
    """Адаптирует публичный сценарий Reference Data к порту профиля Identity."""

    def __init__(self, handler: ValidateCurrencyHandler) -> None:
        """Принимает сценарий проверки на сессии внешнего UoW."""
        self._handler = handler

    async def ensure_supported(self, currency: CurrencyVO) -> None:
        """Проверяет валюту перед изменением предпочтения профиля."""
        await self._handler.execute(ValidateCurrencyQuery(code=currency.value))
