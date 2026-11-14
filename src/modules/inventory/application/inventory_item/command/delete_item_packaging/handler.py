from src.modules.inventory.application.inventory_item.command.delete_item_packaging.command import (
    DeleteItemPackagingCommand,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)


class DeleteItemPackagingHandler:
    """Удаляет дочернюю упаковку через корень InventoryItem в общем внешнем UoW."""

    def __init__(self, repository: InventoryItemRepositoryProtocol) -> None:
        """Принимает порт полного агрегата без доступа к сессии или управлению транзакцией."""
        self._repository = repository

    async def execute(self, command: DeleteItemPackagingCommand) -> None:
        """Блокирует корень, вызывает Domain и сохраняет оставшийся состав без commit."""
        item = await self._repository.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        updated = item.remove_packaging(command.packaging_id)
        await self._repository.save(updated)
