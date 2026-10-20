from src.modules.channels.application.product_representation.query.get_catalog_usage.query import (
    GetCatalogUsageQuery,
)
from src.modules.channels.application.product_representation.query.get_catalog_usage.dto import (
    GetCatalogUsageResultDTO,
)
from src.modules.channels.application.product_representation.port.binding_queries import (
    BindingQueriesPort,
)


class GetCatalogUsageHandler:
    """Публично сообщает владельцу Catalog активное использование товаров."""

    def __init__(self, bindings: BindingQueriesPort) -> None:
        """Принимает read-порт того же внешнего tenant UoW."""
        self.bindings = bindings

    async def execute(self, query: GetCatalogUsageQuery) -> GetCatalogUsageResultDTO:
        """Не восстанавливает корни и не блокирует публикации после item-lock."""
        return GetCatalogUsageResultDTO(await self.bindings.used_ids(query.item_ids))
