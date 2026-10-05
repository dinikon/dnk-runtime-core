from typing import Protocol


class CategoryLocaleReaderPort(Protocol):
    """Проверка активной локали при записи Category."""

    async def is_active(self, code: str) -> bool: ...
