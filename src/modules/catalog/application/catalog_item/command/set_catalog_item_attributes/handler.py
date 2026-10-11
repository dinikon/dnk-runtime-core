from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.attribute_definitions import (
    AttributeDefinitionsPort,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_item.command.set_catalog_item_attributes.command import (
    SetCatalogItemAttributesCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_attributes.dto import (
    SetCatalogItemAttributesResultDTO,
)


class SetCatalogItemAttributesHandler:
    """Координирует set_catalog_item_attributes; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        definitions: AttributeDefinitionsPort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._definitions = definitions

    async def execute(
        self, command: SetCatalogItemAttributesCommand
    ) -> SetCatalogItemAttributesResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        definitions = await self._definitions.get_definitions(
            tuple(v.attribute_id for v in command.values)
        )
        root.set_attributes(
            command.item_id, command.values, definitions, command.actor_id, now
        )
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return SetCatalogItemAttributesResultDTO(
            item.id.uuid, root.id.uuid, item.revision, root.revision
        )
