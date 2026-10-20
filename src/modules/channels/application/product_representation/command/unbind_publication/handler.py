from src.modules.channels.application.product_representation.command.unbind_publication.command import (
    UnbindPublicationCommand,
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
from src.modules.channels.domain.product_representation.repository import (
    ProductRepresentationRepositoryProtocol,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsNotFoundError,
)


class UnbindPublicationHandler:
    """Явно снимает только указанную связь без удаления товара или публикации."""

    def __init__(
        self,
        catalog: CatalogItemsFacade,
        sources: PublicationCatalogSourcePort,
        bindings: BindingQueriesPort,
        repository: ProductRepresentationRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Получает порты item-lock, source-lock и корня на одном UoW."""
        self.catalog, self.sources, self.bindings, self.repository, self.clock = (
            catalog,
            sources,
            bindings,
            repository,
            clock,
        )

    async def execute(self, command: UnbindPublicationCommand) -> None:
        """Позволяет повтор снятой связи, но никогда не снимает новую вместо старой."""
        binding = await self.bindings.binding(command.binding_id)
        if binding is None:
            raise ChannelsNotFoundError("binding_not_found")
        if binding.publication_id != command.publication_id:
            raise ChannelsConflictError("binding_revision_conflict")
        if not binding.active:
            return
        await self.catalog.lock_item(command.tenant_id, binding.catalog_item_id)
        await self.sources.source(command.publication_id, lock=True)
        item = await self.repository.get(EntityIdVO(binding.representation_id))
        item.unbind(
            EntityIdVO(command.binding_id),
            command.expected_revision,
            EntityIdVO(command.actor_id),
            self.clock.now(),
        )
        await self.repository.save(item)
