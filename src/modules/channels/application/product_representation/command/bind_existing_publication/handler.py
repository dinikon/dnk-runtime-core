from src.modules.channels.domain.product_representation.policy import (
    ensure_linking_allowed,
    ensure_target_available,
)
from src.modules.channels.application.product_representation.command.bind_existing_publication.command import (
    BindExistingPublicationCommand,
)
from src.modules.channels.application.product_representation.command.bind_existing_publication.dto import (
    BindExistingPublicationResultDTO,
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
from src.modules.channels.application.product_representation.linking_service import (
    PublicationLinkingService,
)
from src.modules.channels.domain.error import ChannelsConflictError


class BindExistingPublicationHandler:
    """Создаёт только связь, не меняя SKU, тексты, цену или наличие Catalog."""

    def __init__(
        self,
        catalog: CatalogItemsFacade,
        sources: PublicationCatalogSourcePort,
        bindings: BindingQueriesPort,
        linking: PublicationLinkingService,
    ) -> None:
        """Получает все порты одной внешней транзакции."""
        self.catalog, self.sources, self.bindings, self.linking = (
            catalog,
            sources,
            bindings,
            linking,
        )

    async def execute(
        self, command: BindExistingPublicationCommand
    ) -> BindExistingPublicationResultDTO:
        """Соблюдает порядок Catalog item → Channel/source → representation."""
        status = await self.catalog.lock_item(
            command.tenant_id, command.catalog_item_id
        )
        ensure_target_available(status)
        source = await self.sources.source(command.publication_id, lock=True)
        ensure_linking_allowed(source.archived)
        current = await self.bindings.active(command.publication_id)
        if current and current.catalog_item_id != command.catalog_item_id:
            raise ChannelsConflictError("publication_already_bound")
        result = await self.linking.attach(
            source, command.catalog_item_id, command.expected_revision, command.actor_id
        )
        return BindExistingPublicationResultDTO(
            result.catalog_item_id,
            result.representation_id,
            result.binding_id,
            result.revision,
        )
