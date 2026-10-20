from typing import Protocol
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogCandidatesDTO,
)


class CatalogItemsFacade(Protocol):
    """Ограничивает доступ ядра поиском и публичной item-блокировкой Catalog."""

    async def candidates(
        self, tenant_id: UUID, locale: str, search: str | None, offset: int, limit: int
    ) -> CatalogCandidatesDTO:
        """Возвращает страницу поиска самостоятельных товаров."""
        ...

    async def lock_item(self, tenant_id: UUID, item_id: UUID) -> str:
        """Удерживает блокировку владельца до commit и возвращает статус."""
        ...
