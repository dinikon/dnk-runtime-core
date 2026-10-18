from typing import Protocol
from src.modules.shared.domain.value_object.currency import CurrencyVO


class ProfileCurrencyValidatorProtocol(Protocol):
    """Проверяет допустимость явно выбранной валюты профиля."""

    async def ensure_supported(self, currency: CurrencyVO) -> None:
        """Отклоняет отсутствующий либо неактивный код справочника."""
        ...
