"""Адаптер публичных Application-контрактов reference_data."""

from src.modules.channels.application.error import ChannelInputError
from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.application.currency.query.validate_currency.query import (
    ValidateCurrencyQuery,
)
from src.modules.shared.domain.value_object.currency_code_not_supported_error import (
    CurrencyCodeNotSupportedError,
)


class ReferenceChannelSettingsCatalog:
    """Проверяет коды без импорта таблиц чужого модуля."""

    def __init__(
        self, catalog: CatalogRepositoryPort, currencies: ValidateCurrencyHandler
    ) -> None:
        """Получает публичные контракты на общей внешней транзакции."""
        self.catalog, self.currencies = catalog, currencies

    async def ensure_available(
        self, *, currency: str, locales: tuple[str, ...]
    ) -> None:
        """Преобразует отказы справочника в безопасные ошибки формы Channels."""
        try:
            await self.currencies.execute(ValidateCurrencyQuery(code=currency))
        except CurrencyCodeNotSupportedError:
            raise ChannelInputError(
                "currency_unavailable", field="config.settings.currency"
            ) from None
        for locale in locales:
            if not await self.catalog.has_active_locale(locale):
                raise ChannelInputError(
                    "locale_unavailable",
                    field=(
                        "config.settings.locales"
                        if len(locales) > 1
                        else "config.settings.locale"
                    ),
                )
