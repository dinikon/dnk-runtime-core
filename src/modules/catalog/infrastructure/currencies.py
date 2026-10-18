from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError


class ReferenceDataCurrencies:
    """Проверяет валюту через публичный сценарий Reference Data."""

    def __init__(self, handler: ValidateCurrencyHandler) -> None:
        """Принимает handler, собранный на общей сессии."""
        self._handler = handler

    async def ensure_active(self, code: str) -> None:
        """Отклоняет неизвестную или неактивную валюту."""
        try:
            await self._handler.execute(ValidateCurrencyQuery(code))
        except CurrencyCodeNotSupportedError as exc:
            raise InvalidCatalogValueError("Валюта отсутствует или неактивна.") from exc
