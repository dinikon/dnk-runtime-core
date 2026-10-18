from src.modules.reference_data.application.currency.port.query_repository import (
    CurrencyQueryRepositoryProtocol,
)
from src.modules.reference_data.application.currency.query.validate_currency.dto import (
    ValidateCurrencyResultDTO,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)


class ValidateCurrencyHandler:
    """Проверяет форму кода и наличие активной валюты через порт проекций."""

    def __init__(self, repository: CurrencyQueryRepositoryProtocol) -> None:
        """Принимает порт чтения валют на сессии внешнего UoW."""
        self._repository = repository

    async def execute(self, query: ValidateCurrencyQuery) -> ValidateCurrencyResultDTO:
        """Возвращает конкретный DTO или отклоняет неизвестный и неактивный код."""
        code = CurrencyVO.from_value(query.code).value
        result = await self._repository.get_active(code)
        if result is None:
            raise CurrencyCodeNotSupportedError(code)
        return result
