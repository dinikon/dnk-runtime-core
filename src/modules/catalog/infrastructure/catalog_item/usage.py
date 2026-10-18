from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class UnboundCatalogItemUsage:
    """MVP без Catalog bindings; заменяется портом потребителя при их появлении."""

    async def used_ids(
        self, identifiers: tuple[CatalogItemIdVO, ...]
    ) -> frozenset[CatalogItemIdVO]:
        """Возвращает пустой набор, пока внешние связи с CatalogItem отсутствуют."""
        return frozenset()
