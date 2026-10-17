from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_item.command.set_catalog_item_stock.command import (
    SetCatalogItemStockCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_stock.dto import (
    SetCatalogItemStockResultDTO,
)


class SetCatalogItemStockHandler:
    """Координирует set_catalog_item_stock; товарные инварианты остаются в CatalogItem."""

    def __init__(self, mutations: CatalogItemMutationService, clock: ClockPort) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock

    async def execute(
        self, command: SetCatalogItemStockCommand
    ) -> SetCatalogItemStockResultDTO:
        """Загружает товар, вызывает доменный метод и сохраняет изменение без commit."""
        item = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_revision
        )
        now = self._clock.now()
        item.set_stock(command.stock, command.actor_id, now)
        await self._mutations.save(item)
        return SetCatalogItemStockResultDTO(item.id.uuid, item.revision)
