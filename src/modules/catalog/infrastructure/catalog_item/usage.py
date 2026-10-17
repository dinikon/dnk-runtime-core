from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class UnboundCatalogItemUsage:
    """MVP без Catalog bindings; заменяется портом потребителя при их появлении."""

    async def used_ids(
        self, identifiers: tuple[CatalogItemIdVO, ...]
    ) -> frozenset[CatalogItemIdVO]:
        """Текущие observed Channels не содержат связей с CatalogItem."""
        return frozenset()
