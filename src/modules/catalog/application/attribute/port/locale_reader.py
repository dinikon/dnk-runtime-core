from typing import Protocol


class AttributeLocaleReaderPort(Protocol):
    async def is_active(self, code: str) -> bool: ...
