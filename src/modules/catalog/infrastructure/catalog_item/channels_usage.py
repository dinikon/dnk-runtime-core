from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.channels.application.product_representation.query.get_catalog_usage.handler import (
    GetCatalogUsageHandler,
)
from src.modules.channels.application.product_representation.query.get_catalog_usage.query import (
    GetCatalogUsageQuery,
)


class ChannelsCatalogItemUsage:
    """Адаптирует публичный контракт Channels к собственному порту usage Catalog."""

    def __init__(self, handler: GetCatalogUsageHandler) -> None:
        """Принимает публичный read handler на той же внешней сессии."""
        self.handler = handler

    async def used_ids(
        self, identifiers: tuple[CatalogItemIdVO, ...]
    ) -> frozenset[CatalogItemIdVO]:
        """Проверяет ссылки после захвата item-lock владельцем Catalog."""
        result = await self.handler.execute(
            GetCatalogUsageQuery(tuple(i.uuid for i in identifiers))
        )
        return frozenset(CatalogItemIdVO(identifier) for identifier in result.item_ids)
