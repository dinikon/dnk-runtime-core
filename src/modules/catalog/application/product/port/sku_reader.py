from typing import Protocol
from uuid import UUID


class SkuReaderPort(Protocol):
    """Catalog читает только нужные ему данные Inventory.SKU."""

    async def get_code(self, sku_id: UUID) -> str | None: ...

    async def get_codes(self, sku_ids: tuple[UUID, ...]) -> dict[UUID, str]: ...
