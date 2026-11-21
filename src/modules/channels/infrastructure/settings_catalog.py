"""Адаптер справочников Reference Data для настроек подключения."""

from src.modules.channels.application.error import ChannelInputError
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)


class ReferenceDataChannelSettings:
    """Использует публичные Application-контракты владельца справочников."""

    def __init__(
        self, currencies: ValidateCurrencyHandler, locales: CatalogRepositoryPort
    ) -> None:
        """Принимает зависимости на сессии общей транзакции Channels."""
        self._currencies, self._locales = currencies, locales

    async def ensure_available(
        self, *, currency: str, locales: tuple[str, ...]
    ) -> None:
        """Проверяет коды без прямого чтения SQL-моделей другого модуля."""
        try:
            await self._currencies.execute(ValidateCurrencyQuery(currency))
        except CurrencyCodeNotSupportedError:
            raise ChannelInputError(
                "currency_unavailable", field="config.settings.currency"
            ) from None
        for locale in locales:
            if not await self._locales.has_active_locale(locale):
                raise ChannelInputError("locale_unavailable", field="config.settings")
