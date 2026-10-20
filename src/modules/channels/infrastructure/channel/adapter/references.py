from src.modules.channels.application.plugin_contract import (
    ConnectionSettingsReferencesDTO,
)
from src.modules.channels.domain.error import ChannelsValidationError
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


class ConnectionReferencesAdapter:
    """Обращается к публичным контрактам владельца глобальных кодов."""

    def __init__(
        self, catalog: CatalogRepositoryPort, currency: ValidateCurrencyHandler
    ) -> None:
        """Принимает контракт справочника и Application сценарий валют на общем UoW."""
        self.catalog, self.currency = (catalog, currency)

    async def validate(self, references: ConnectionSettingsReferencesDTO) -> None:
        """Проверяет каждую выбранную locale и optional валюту без foreign ORM."""
        for code in references.locales:
            if not await self.catalog.has_active_locale(code):
                raise ChannelsValidationError("locale_not_supported")
        for currency in references.currencies:
            try:
                await self.currency.execute(ValidateCurrencyQuery(currency))
            except CurrencyCodeNotSupportedError:
                raise ChannelsValidationError("currency_not_supported") from None
