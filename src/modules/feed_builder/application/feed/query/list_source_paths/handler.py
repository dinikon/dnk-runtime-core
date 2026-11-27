from src.modules.feed_builder.application.feed.query.list_source_paths.query import (
    ListSourcePathsQuery,
)
from src.modules.feed_builder.application.feed.query.list_source_paths.dto import (
    ListSourcePathsResultDTO,
    SourcePathItemDTO,
)
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.source_provider import SourceProvider
from src.modules.feed_builder.domain.feed.policy.schema_sources import (
    FeedSchemaSourcePolicy,
)


class ListSourcePathsHandler:
    """Описывает источники из закрытого Domain-контракта, не читая товары."""

    async def execute(self, query: ListSourcePathsQuery) -> ListSourcePathsResultDTO:
        """Сохраняет совпадение реестра с Domain Policy совместимости."""
        labels = {
            CatalogSourcePath.TITLE: "Название товара",
            CatalogSourcePath.DESCRIPTION: "Описание товара",
            CatalogSourcePath.DESCRIPTION_HTML: "Описание товара (HTML)",
            CatalogSourcePath.SKU: "SKU товара",
            CatalogSourcePath.REGULAR_PRICE: "Обычная цена",
            CatalogSourcePath.STOCK_QUANTITY: "Остаток",
            CatalogSourcePath.IN_STOCK: "В наличии",
        }
        return ListSourcePathsResultDTO(
            tuple(
                SourcePathItemDTO(
                    SourceProvider.CATALOG.value,
                    path.value,
                    labels[path],
                    tuple(
                        kind.value
                        for kind in FeedSchemaSourcePolicy.allowed_kinds(path)
                    ),
                    FeedSchemaSourcePolicy.requires_locale(path),
                )
                for path in CatalogSourcePath
            )
        )
