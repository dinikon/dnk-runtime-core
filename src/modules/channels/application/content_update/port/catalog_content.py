from typing import Protocol
from uuid import UUID
from src.modules.channels.domain.content_update.value_object.texts import ContentTextsVO


class CatalogContentFacade(Protocol):
    """Читает тексты Catalog через публичную границу владельца."""

    async def snapshot(
        self, tenant_id: UUID, item_ids: tuple[UUID, ...], locales: tuple[str, ...]
    ) -> dict[UUID, ContentTextsVO]:
        """Фиксирует обе локали под item-lock без создания второго источника контента."""
        ...
