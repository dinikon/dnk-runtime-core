from typing import Protocol
from uuid import UUID


class CategoryReaderPort(Protocol):
    async def require_all(self, category_ids: tuple[UUID, ...]) -> None: ...
