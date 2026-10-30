from typing import Protocol


class FeedSourcePort(Protocol):
    """Получает полный ограниченный документ вне SQL-транзакции."""

    def validate_url(self, url: str) -> str:
        """Проверяет публичный URL без раскрытия query-параметров."""
        ...

    async def fetch(self, url: str) -> bytes:
        """Не принимает redirect, неполный HTTP-ответ и превышение лимита."""
        ...
