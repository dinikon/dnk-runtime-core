from src.modules.reference_data.application.currency.port.validation_catalog import (
    CurrencyValidationCatalogQueryRepositoryProtocol,
)
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)


class ReferenceReceiptCurrencies:
    """Проверяет валюты через публичный batch-контракт Reference Data без чужих ORM."""

    def __init__(
        self, catalog: CurrencyValidationCatalogQueryRepositoryProtocol
    ) -> None:
        """Получает публичный порт общей транзакции."""
        self._catalog = catalog

    async def ensure_codes(self, codes: tuple[str, ...]) -> None:
        """Требует активную запись для каждой известной суммы нового основания."""
        if not codes:
            return
        found = {value.code for value in await self._catalog.get_active_codes(codes)}
        for code in codes:
            if code not in found:
                raise CurrencyCodeNotSupportedError(code)
