from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.classification_references import (
    ClassificationReferencesPort,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.application.catalog_item.command.set_catalog_item_categories.command import (
    SetCatalogItemCategoriesCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_categories.dto import (
    SetCatalogItemCategoriesResultDTO,
)


class SetCatalogItemCategoriesHandler:
    """Координирует set_catalog_item_categories; товарные инварианты остаются в CatalogItem."""

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
        self, command: SetCatalogItemCategoriesCommand
    ) -> SetCatalogItemCategoriesResultDTO:
        """Загружает товар, вызывает доменный метод и сохраняет изменение без commit."""
        item = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_revision
        )
        now = self._clock.now()
        existing = await self._references.categories(
            tuple(CategoryIdVO(i) for i in command.category_ids)
        )
        item.set_categories(
            tuple(CategoryIdVO(i) for i in command.category_ids),
            (
                CategoryIdVO(command.primary_category_id)
                if command.primary_category_id
                else None
            ),
            existing,
            command.actor_id,
            now,
        )
        await self._mutations.save(item)
        return SetCatalogItemCategoriesResultDTO(item.id.uuid, item.revision)
