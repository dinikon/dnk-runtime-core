from typing import Protocol
from src.modules.currency.domain.aggregate import ExchangeRateBook


class ExchangeRateBookRepositoryProtocol(Protocol):
    """Загружает и сохраняет книгу вместе со всеми принадлежащими ей котировками."""

    async def get(self) -> ExchangeRateBook | None:
        """Восстанавливает текущую книгу или возвращает отсутствие первой загрузки."""
        ...

    async def save(self, book: ExchangeRateBook) -> None:
        """Атомарно сохраняет агрегат в общей транзакции без commit."""
        ...
