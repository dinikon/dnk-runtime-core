from src.modules.catalog.application.catalog_category.query.list_catalog_categories.repository import (
    CatalogCategoryQueryRepositoryProtocol,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.feed_builder.application.feed.port.catalog_category_tree import (
    SourceCategoryDTO,
)


class CatalogCategoryTree:
    """Преобразует публичный контракт исходного дерева в данные Feed Builder."""

    def __init__(self, categories: CatalogCategoryQueryRepositoryProtocol) -> None:
        """Принимает read-side Catalog в текущей tenant-транзакции."""
        self._categories = categories

    async def read(self, locale: str) -> tuple[SourceCategoryDTO, ...]:
        """Берёт запрошенное название или доступную резервную локаль Catalog."""
        tree = await self._categories.list_tree(LocaleVO(locale))
        return tuple(
            SourceCategoryDTO(node.id, node.parent_id, node.name or node.fallback_name)
            for node in tree.items
        )
