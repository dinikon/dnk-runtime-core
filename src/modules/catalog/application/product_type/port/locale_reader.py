from typing import Protocol


class ProductTypeLocaleReaderPort(Protocol):
    async def is_active(self, code: str) -> bool: ...
