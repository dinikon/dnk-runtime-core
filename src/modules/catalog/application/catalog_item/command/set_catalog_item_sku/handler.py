from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.command import (
    SetCatalogItemSkuCommand,
)
from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.dto import (
    SetCatalogItemSkuResultDTO,
)
from src.modules.catalog.application.catalog_item.inventory_service import (
    CatalogItemInventoryService,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SetCatalogItemSkuHandler:
    """Связывает SKU и карточку одной атомарной командой без вложенного UoW."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        inventory: CatalogItemInventoryService,
        clock: ClockPort,
    ) -> None:
        """Принимает только порты и координаторы текущей транзакции."""
        self._mutations, self._inventory, self._clock = mutations, inventory, clock

    async def execute(
        self, command: SetCatalogItemSkuCommand
    ) -> SetCatalogItemSkuResultDTO:
        """Загружает корень, разрешает ссылку и вызывает доменный метод назначения."""
        root = await self._mutations.load(command.tenant_id, command.item_id)
        target_id = command.variant_id or root.id
        if command.variant_id is not None:
            root.variant(command.variant_id)
        elif (
            root.kind is CatalogItemKind.VARIABLE and command.selection.mode != "clear"
        ):
            raise InvalidCatalogValueError(
                "Контейнер VARIABLE не имеет собственного SKU.", ("sku",)
            )
        reference = await self._inventory.resolve(command.selection, target_id.uuid)
        root.set_inventory_item(
            identifier=EntityIdVO(reference.id) if reference else None,
            actor=command.actor_id,
            now=self._clock.now(),
            target_id=target_id,
        )
        await self._mutations.save(root)
        return SetCatalogItemSkuResultDTO(
            target_id.uuid,
            reference.id if reference else None,
            reference.sku if reference else None,
            reference.created if reference else False,
        )
