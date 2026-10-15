from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.port.currencies import CurrencyPort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_item.command.set_catalog_item_price.command import (
    SetCatalogItemPriceCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_price.dto import (
    SetCatalogItemPriceResultDTO,
)


class SetCatalogItemPriceHandler:
    """Координирует set_catalog_item_price; товарные инварианты остаются в CatalogItem."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        currencies: CurrencyPort,
    ) -> None:
        """Принимает порты конкретного сценария на общей tenant UoW."""
        self._mutations = mutations
        self._clock = clock
        self._currencies = currencies

    async def execute(
        self, command: SetCatalogItemPriceCommand
    ) -> SetCatalogItemPriceResultDTO:
        """Загружает семью, вызывает доменный метод и сохраняет изменение без commit."""
        root = await self._mutations.load(
            command.tenant_id, command.item_id, command.expected_root_revision
        )
        now = self._clock.now()
        if command.price is not None:
            await self._currencies.ensure_active(command.price.currency)
        root.set_price(command.item_id, command.price, command.actor_id, now)
        await self._mutations.save(root)
        item = root.find_item(command.item_id)
        return SetCatalogItemPriceResultDTO(
            item.id.uuid, root.id.uuid, item.revision, root.revision
        )
