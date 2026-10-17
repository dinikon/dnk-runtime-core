from typing import Protocol


class ExchangeRatePublicationLockProtocol(Protocol):
    """Сериализует публикацию книги в общей транзакции, включая первую загрузку."""

    async def acquire(self) -> None:
        """Удерживает распределённую блокировку до завершения внешнего UoW."""
        ...
