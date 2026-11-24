from typing import Protocol
from uuid import UUID


class PublicFeedTenantResolverPort(Protocol):
    """Разрешает tenant публичной выдачи из хоста запроса."""

    async def resolve(self, host: str) -> UUID | None:
        """Возвращает tenant с разрешённым чтением на соединении запроса."""
        ...
