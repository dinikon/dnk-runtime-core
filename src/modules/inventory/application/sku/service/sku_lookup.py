from uuid import UUID

from src.modules.inventory.application.sku.port.query_repository import (
    SkuQueryRepositoryProtocol,
)
from src.modules.inventory.application.sku.port.sku_lookup import SkuReferenceDTO
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO


class SkuLookupService:
    """Публичное чтение идентичности через tenant-scoped query repository."""

    def __init__(self, repository: SkuQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def get_sku(self, *, sku_id: UUID) -> SkuReferenceDTO | None:
        """Проверяет ссылку будущего Variant и возвращает только application DTO."""
        result = await self._repository.get_details(sku_id=SkuIdVO.from_value(sku_id))
        if result is None:
            return None
        return SkuReferenceDTO(id=result.id, code=result.code, title=result.title)
