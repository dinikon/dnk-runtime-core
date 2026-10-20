from typing import Protocol
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogBindingDTO,
)


class BindingQueriesPort(Protocol):
    """Читает проекции существующих ссылок без восстановления корней."""

    async def active(self, publication_id: UUID) -> CatalogBindingDTO | None:
        """Находит действующую связь выбранной публикации."""
        ...

    async def binding(self, binding_id: UUID) -> CatalogBindingDTO | None:
        """Находит конкретный исторический binding для безопасного снятия."""
        ...

    async def occupied(
        self, connection_id: UUID, item_ids: tuple[UUID, ...]
    ) -> frozenset[UUID]:
        """Возвращает товары с основной активной публикацией этого Connection."""
        ...

    async def used_ids(self, item_ids: tuple[UUID, ...]) -> frozenset[UUID]:
        """Возвращает активное использование Catalog независимо от архива канала."""
        ...

    async def versions(
        self, connection_id: UUID, item_ids: tuple[UUID, ...]
    ) -> dict[UUID, int]:
        """Возвращает версии существующих представлений для условного bind."""
        ...
