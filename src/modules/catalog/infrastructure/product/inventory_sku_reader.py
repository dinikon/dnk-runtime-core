from uuid import UUID

from src.modules.inventory.application.sku.port.query_repository import (
    SkuQueryRepositoryProtocol,
)
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO


class InventorySkuReaderAdapter:
    """Переход из Catalog к публичному read-контракту Inventory."""

    def __init__(self, repository: SkuQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def get_code(self, sku_id: UUID) -> str | None:
        details = await self._repository.get_details(sku_id=SkuIdVO.from_value(sku_id))
        return None if details is None else details.code

    async def get_codes(self, sku_ids: tuple[UUID, ...]) -> dict[UUID, str]:
        return await self._repository.get_codes(sku_ids=sku_ids)
