from src.modules.inventory.application.inventory_item.command.update_item_packaging.command import (
    UpdateItemPackagingCommand,
)
from src.modules.inventory.application.inventory_item.command.update_item_packaging.dto import (
    UpdateItemPackagingResultDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
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


class UpdateItemPackagingHandler:
    """Координирует изменение упаковки через корень InventoryItem и актуальный снимок тары."""

    def __init__(
        self,
        items: InventoryItemRepositoryProtocol,
        types: PackagingTypeRepositoryProtocol,
    ) -> None:
        """Принимает два write-порта одной сессии внешнего tenant-UoW."""
        self._items = items
        self._types = types

    async def execute(
        self, command: UpdateItemPackagingCommand
    ) -> UpdateItemPackagingResultDTO:
        """Блокирует товар перед итоговым типом, применяет Domain и пропускает запись no-op."""
        item = await self._items.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        current = item.get_packaging(command.packaging_id)
        type_id = (
            command.packaging_type_id
            if "packaging_type_id" in command.fields
            and command.packaging_type_id is not None
            else current.packaging_type_id
        )
        kind = await self._types.get_for_update(type_id)
        if kind is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")
        updated = item.change_packaging(
            identifier=current.id,
            packaging_type=kind.snapshot(),
            code=(
                PackagingCodeVO(command.code)
                if "code" in command.fields and command.code is not None
                else current.code
            ),
            name=(
                PackagingNameVO(command.name)
                if "name" in command.fields and command.name is not None
                else current.name
            ),
            content_quantity=(
                PackagingQuantityVO(command.content_quantity)
                if "content_quantity" in command.fields
                and command.content_quantity is not None
                else current.content_quantity
            ),
            content_uom=(
                UomCodeVO(command.content_uom)
                if "content_uom" in command.fields and command.content_uom is not None
                else current.content_uom
            ),
        )
        if updated is not item:
            await self._items.save(updated)
        packaging = updated.get_packaging(current.id)
        return UpdateItemPackagingResultDTO(
            id=packaging.id.uuid,
            inventory_item_id=updated.id.uuid,
            packaging_type_id=packaging.packaging_type_id.uuid,
            code=packaging.code.value,
            name=packaging.name.value,
            content_quantity=packaging.content_quantity.value,
            content_uom=packaging.content_uom.value,
        )
