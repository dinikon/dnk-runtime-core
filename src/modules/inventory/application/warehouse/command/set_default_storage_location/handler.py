from src.modules.inventory.application.warehouse.command.set_default_storage_location.command import (
    SetDefaultStorageLocationCommand,
)
from src.modules.inventory.application.warehouse.command.set_default_storage_location.dto import (
    SetDefaultStorageLocationResultDTO,
)
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)


class SetDefaultStorageLocationHandler:
    """Координирует назначение основной локации через Domain в общем tenant-UoW."""

    def __init__(
        self,
        warehouses: WarehouseRepositoryProtocol,
        locations: StockLocationRepositoryProtocol,
    ) -> None:
        """Принимает write-порты одной транзакции без доступа к сессии и commit."""
        self._warehouses = warehouses
        self._locations = locations

    async def execute(
        self, command: SetDefaultStorageLocationCommand
    ) -> SetDefaultStorageLocationResultDTO:
        """Блокирует склад, затем адрес, вызывает Domain и сохраняет только изменение."""
        warehouse = await self._warehouses.get_for_update(command.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        location = await self._locations.get_for_update(
            command.location_id, warehouse_id=command.warehouse_id
        )
        if location is None:
            raise StockLocationNotFoundError("Локация не найдена в указанном складе.")
        updated = warehouse.set_default_storage_location(location.snapshot())
        if updated != warehouse:
            await self._warehouses.save(updated)
        return SetDefaultStorageLocationResultDTO(
            id=updated.id.uuid,
            code=updated.code.value,
            name=updated.name.value,
            is_active=updated.is_active,
            default_storage_location_id=location.id.uuid,
        )
