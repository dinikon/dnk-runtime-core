from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_item.command.set_catalog_item_status.command import (
    SetCatalogItemStatusCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_status.dto import (
    SetCatalogItemStatusResultDTO,
)


class SetCatalogItemStatusHandler:
    """Координирует set_catalog_item_status; товарные инварианты остаются в CatalogItem."""

    def __init__(self, mutations: CatalogItemMutationService, clock: ClockPort) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock

    async def execute(
        self, command: SetCatalogItemStatusCommand
    ) -> SetCatalogItemStatusResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        root.set_status(command.item_id, command.status, command.actor_id, now)
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return SetCatalogItemStatusResultDTO(
            item.id.uuid, root.id.uuid, item.revision, root.revision
        )
