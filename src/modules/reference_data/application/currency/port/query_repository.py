from typing import Protocol

from src.modules.reference_data.application.currency.query.validate_currency.dto import (
    ValidateCurrencyResultDTO,
)


class CurrencyQueryRepositoryProtocol(Protocol):
    """Контракт чтения валют для проверки кода без выдачи Domain или ORM."""

    async def get_active(self, code: str) -> ValidateCurrencyResultDTO | None:
        """Возвращает сведения об активной валюте или отсутствие кода."""
        ...
