from src.modules.channels.domain.product_representation.policy import (
    ensure_linking_allowed,
)
from src.modules.channels.application.product_representation.query.preview_catalog_draft.query import (
    PreviewCatalogDraftQuery,
)
from src.modules.channels.application.product_representation.query.preview_catalog_draft.dto import (
    PreviewCatalogDraftResultDTO,
)
from src.modules.channels.application.product_representation.port.catalog_drafts import (
    CatalogDraftCreationFacade,
)
from src.modules.channels.application.product_representation.port.publication_catalog import (
    PublicationCatalogSourcePort,
)
from src.modules.channels.application.product_representation.port.binding_queries import (
    BindingQueriesPort,
)
from src.modules.channels.application.product_representation.draft_policy import (
    proposed_draft,
)
from src.modules.channels.domain.error import ChannelsConflictError


class PreviewCatalogDraftHandler:
    """Предлагает перенос сохранённого snapshot и проверяет его правилами Catalog."""

    def __init__(
        self,
        sources: PublicationCatalogSourcePort,
        catalog: CatalogDraftCreationFacade,
        bindings: BindingQueriesPort,
    ) -> None:
        """Получает порты read-side и проверки значений без записи."""
        self.sources, self.catalog, self.bindings = sources, catalog, bindings

    async def execute(
        self, query: PreviewCatalogDraftQuery
    ) -> PreviewCatalogDraftResultDTO:
        """Не вызывает внешнюю площадку и не создаёт persistent товар."""
        source = await self.sources.source(query.publication_id)
        ensure_linking_allowed(source.archived)
        if await self.bindings.active(query.publication_id):
            raise ChannelsConflictError("publication_already_bound")
        if source.observed_revision != query.expected_observed_revision:
            raise ChannelsConflictError("publication_revision_conflict")
        values = proposed_draft(source, query.locale)
        checked = await self.catalog.validate(query.tenant_id, query.actor_id, values)
        return PreviewCatalogDraftResultDTO(
            source.observed_revision,
            values,
            checked.issues,
            source.warnings,
            source.main_image_url,
            {
                "titles": "source.title/title_locale",
                "sku": "source.external_sku",
                "regular_price": "source.price",
                "sale_price": "source.sale_price",
                "currency": "source.currency",
                "quantity": "source.quantity",
                "stock_status": "source.stock_status",
                "backorders": "explicit_default_no",
            },
        )
