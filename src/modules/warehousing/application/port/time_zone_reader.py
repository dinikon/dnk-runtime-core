from typing import Protocol


class TimeZoneReaderProtocol(Protocol):
    """Проверка активности кода timezone через публичный контракт Reference Data."""

    async def is_active(self, code: str) -> bool:
        """Возвращает признак допустимости кода без передачи чужих Domain-объектов."""
        ...
