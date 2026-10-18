from typing import Protocol

from src.modules.shared.domain.value_object.currency import CurrencyVO


class CurrencyValidatorProtocol(Protocol):
    """Порт проверки валюты Tenant через внешний контекст справочников."""

    async def ensure_supported(self, currency: CurrencyVO) -> None:
        """Отклоняет код, отсутствующий в активном справочнике валют."""
        ...
