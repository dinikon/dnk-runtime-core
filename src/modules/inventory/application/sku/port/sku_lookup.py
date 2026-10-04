from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SkuReferenceDTO:
    """Публичная идентичность SKU для ссылок Catalog и других контекстов."""

    id: UUID
    code: str
    title: str


class SkuLookupProtocol(Protocol):
    """Проверка SKU в текущем tenant без экспорта domain или ORM-модели."""

    async def get_sku(self, *, sku_id: UUID) -> SkuReferenceDTO | None:
        """Возвращает ссылку на SKU, либо None; количества этим портом не выдаются."""
        ...
