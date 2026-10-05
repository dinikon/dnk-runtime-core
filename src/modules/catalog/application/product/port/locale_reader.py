from typing import Protocol


class LocaleReaderPort(Protocol):
    """Проверка активного глобального кода без доступа Catalog к public SQL."""

    async def is_active(self, code: str) -> bool: ...
