from typing import Protocol
from uuid import UUID


class InventoryStockOwnerUsageProtocol(Protocol):
    """Публично сообщает об использовании компании владельцем складского документа."""

    async def is_owner_used(self, identifier: UUID) -> bool:
        """Учитывает документы независимо от статуса."""
        ...
