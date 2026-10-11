from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_item.command.delete_catalog_item_content.command import (
    DeleteCatalogItemContentCommand,
)


class DeleteCatalogItemContentHandler:
    """Координирует delete_catalog_item_content; товарные инварианты остаются в CatalogItem."""

    def __init__(self, mutations: CatalogItemMutationService, clock: ClockPort) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock

    async def execute(self, command: DeleteCatalogItemContentCommand) -> None:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        root.delete_content(
            command.item_id, LocaleVO(command.locale), command.actor_id, now
        )
        await self._mutations.save(root)
