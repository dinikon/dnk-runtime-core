from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.classification_references import (
    ClassificationReferencesPort,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.application.catalog_item.command.set_catalog_item_tags.command import (
    SetCatalogItemTagsCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_tags.dto import (
    SetCatalogItemTagsResultDTO,
)


class SetCatalogItemTagsHandler:
    """Координирует set_catalog_item_tags; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        references: ClassificationReferencesPort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._references = references

    async def execute(
        self, command: SetCatalogItemTagsCommand
    ) -> SetCatalogItemTagsResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        existing = await self._references.tags(
            tuple(TagIdVO(i) for i in command.tag_ids)
        )
        root.set_tags(
            command.item_id,
            tuple(TagIdVO(i) for i in command.tag_ids),
            existing,
            command.actor_id,
            now,
        )
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return SetCatalogItemTagsResultDTO(
            item.id.uuid, root.id.uuid, item.revision, root.revision
        )
