from typing import Protocol

from src.modules.inventory.application.sku.query.get_sku.dto import SkuDetailsDTO
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO


class SkuQueryRepositoryProtocol(Protocol):
    """Чтение SKU только из tenant, к которому привязан внешний UoW."""

    async def get_details(self, *, sku_id: SkuIdVO) -> SkuDetailsDTO | None: ...

    async def list_details(self, *, limit: int, offset: int) -> list[SkuDetailsDTO]: ...
