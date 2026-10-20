from src.modules.channels.application.product_representation.query.list_catalog_candidates.query import (
    ListCatalogCandidatesQuery,
)
from src.modules.channels.application.product_representation.query.list_catalog_candidates.dto import (
    ListCatalogCandidatesResultDTO,
    ListCatalogCandidatesItemDTO,
)
from src.modules.channels.application.product_representation.port.catalog_items import (
    CatalogItemsFacade,
)
from src.modules.channels.application.product_representation.port.publication_catalog import (
    PublicationCatalogSourcePort,
)
from src.modules.channels.application.product_representation.port.binding_queries import (
    BindingQueriesPort,
)


class ListCatalogCandidatesHandler:
    """Собирает страницу поиска и локальную доступность без чужих ORM joins."""

    def __init__(
        self,
        sources: PublicationCatalogSourcePort,
        catalog: CatalogItemsFacade,
        bindings: BindingQueriesPort,
    ) -> None:
        """Принимает публичный Catalog facade и локальные read-порты."""
        self.sources, self.catalog, self.bindings = sources, catalog, bindings

    async def execute(
        self, query: ListCatalogCandidatesQuery
    ) -> ListCatalogCandidatesResultDTO:
        """Помечает недоступные строки, сохраняя честный total исходной страницы."""
        source = await self.sources.source(query.publication_id)
        page = await self.catalog.candidates(
            query.tenant_id, query.locale, query.search, query.offset, query.limit
        )
        ids = tuple(item.id for item in page.items)
        occupied = await self.bindings.occupied(source.connection_id, ids)
        versions = await self.bindings.versions(source.connection_id, ids)
        current = await self.bindings.active(query.publication_id)
        rows = []
        for item in page.items:
            reason = (
                "channel_archived"
                if source.archived
                else (
                    "publication_already_bound"
                    if current
                    else (
                        "catalog_item_archived"
                        if item.status == "archived"
                        else (
                            "catalog_item_already_bound"
                            if item.id in occupied
                            else None
                        )
                    )
                )
            )
            rows.append(
                ListCatalogCandidatesItemDTO(
                    item.id,
                    item.title,
                    item.sku,
                    item.status,
                    reason is None,
                    reason,
                    versions.get(item.id),
                )
            )
        return ListCatalogCandidatesResultDTO(tuple(rows), page.total)
