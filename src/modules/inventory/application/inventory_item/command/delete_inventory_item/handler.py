from src.modules.inventory.application.inventory_item.command.delete_inventory_item.command import (
    DeleteInventoryItemCommand,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError
from src.modules.inventory.domain.inventory_item.repository import (
    InventoryItemRepositoryProtocol,
)
from src.modules.inventory.application.inventory_item.port.usage import (
    InventoryItemUsagePort,
)


class DeleteInventoryItemHandler:
    """Удаляет существующий агрегат в транзакции внешнего UoW."""

    def __init__(
        self, repository: InventoryItemRepositoryProtocol, usage: InventoryItemUsagePort
    ) -> None:
        """Принимает порт загрузки и удаления полного агрегата."""
        self._repository = repository
        self._usage = usage

    async def execute(self, command: DeleteInventoryItemCommand) -> None:
        """Блокирует корень и передаёт загруженный агрегат порту удаления."""
        item = await self._repository.get_for_update(command.inventory_item_id)
        if item is None:
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        item.ensure_can_delete(await self._usage.get(item.id))
        await self._repository.delete(item)
