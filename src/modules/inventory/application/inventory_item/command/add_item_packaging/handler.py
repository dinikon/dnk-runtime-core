from src.modules.inventory.application.inventory_item.command.add_item_packaging.command import (
    AddItemPackagingCommand,
)
from src.modules.inventory.application.inventory_item.command.add_item_packaging.dto import (
    AddItemPackagingResultDTO,
)
from src.modules.inventory.domain.inventory_item.entity.item_packaging import (
    ItemPackaging,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.packaging_quantity import (
    PackagingQuantityVO,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError
from src.modules.inventory.domain.packaging_type.repository import (
    PackagingTypeRepositoryProtocol,
)
from src.modules.inventory.domain.value_object.packaging_code import PackagingCodeVO
from src.modules.inventory.domain.value_object.packaging_name import PackagingNameVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class AddItemPackagingHandler:
    """Координирует назначение активной тары и запись полного агрегата товара."""

    def __init__(
        self,
        items: InventoryItemRepositoryProtocol,
        types: PackagingTypeRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общей сессии внешнего UoW и генератор UUID."""
        self._items = items
        self._types = types
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: AddItemPackagingCommand
    ) -> AddItemPackagingResultDTO:
        """Блокирует товар перед типом тары, вызывает Domain и сохраняет без commit."""
        item = await self._items.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        kind = await self._types.get_for_update(command.packaging_type_id)
        if kind is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")
        packaging = ItemPackaging.create(
            identifier=ItemPackagingIdVO.from_value(self._uuid_generator.new()),
            packaging_type_id=kind.id,
            code=PackagingCodeVO(command.code),
            name=PackagingNameVO(command.name),
            content_quantity=PackagingQuantityVO(command.content_quantity),
            content_uom=UomCodeVO(command.content_uom),
        )
        updated = item.add_packaging(packaging, packaging_type=kind.snapshot())
        await self._items.save(updated)
        return AddItemPackagingResultDTO(
            id=packaging.id.uuid,
            inventory_item_id=item.id.uuid,
            packaging_type_id=packaging.packaging_type_id.uuid,
            code=packaging.code.value,
            name=packaging.name.value,
            content_quantity=packaging.content_quantity.value,
            content_uom=packaging.content_uom.value,
        )
