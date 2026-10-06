from typing import Protocol


class ContentBlockLocaleReaderPort(Protocol):
    async def is_active(self, code: str) -> bool: ...
