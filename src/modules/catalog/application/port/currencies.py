from typing import Protocol


class CurrencyPort(Protocol):
    """Проверяет активные валюты публичным контрактом reference_data."""

    async def ensure_active(self, code: str) -> None:
        """Отклоняет неизвестный или неактивный код валюты."""
        ...
