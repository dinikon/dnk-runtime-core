from typing import Protocol


class DealCurrencyCatalogPort(Protocol):
    """Доступные валюты CRM без изменения глобального reference_data."""

    def list(self) -> tuple[tuple[str, str], ...]:
        """Возвращает коды и названия валют продаж."""
        ...
