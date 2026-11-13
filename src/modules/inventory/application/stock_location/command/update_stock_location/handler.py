from src.modules.inventory.application.stock_location.command.update_stock_location.command import (
    UpdateStockLocationCommand,
)
from src.modules.inventory.application.stock_location.command.update_stock_location.dto import (
    UpdateStockLocationResultDTO,
)
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)


class UpdateStockLocationHandler:
    """Координирует изменение локации через Domain внутри внешнего tenant-UoW."""

    def __init__(
        self,
        warehouses: WarehouseRepositoryProtocol,
        locations: StockLocationRepositoryProtocol,
    ) -> None:
        """Принимает write-порты одной сессии без управления транзакцией."""
        self._warehouses = warehouses
        self._locations = locations

    async def execute(
        self, command: UpdateStockLocationCommand
    ) -> UpdateStockLocationResultDTO:
        """Блокирует сначала склад, затем адрес, применяет Domain и пропускает no-op."""
        warehouse = await self._warehouses.get_for_share(command.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        location = await self._locations.get_for_update(
            command.location_id, warehouse_id=command.warehouse_id
        )
        if location is None:
            raise StockLocationNotFoundError("Локация не найдена в указанном складе.")
        updated = location
        if "code" in command.fields and command.code is not None:
            updated = updated.change_code(LocationCodeVO(command.code))
        if "name" in command.fields and command.name is not None:
            updated = updated.rename(LocationNameVO(command.name))
        if "is_active" in command.fields:
            updated = (
                updated.activate()
                if command.is_active
                else updated.deactivate(warehouse=warehouse.snapshot())
            )
        if updated != location:
            await self._locations.save(updated)
        return UpdateStockLocationResultDTO(
            id=updated.id.uuid,
            warehouse_id=updated.warehouse_id.uuid,
            parent_location_id=(
                updated.parent_location_id.uuid
                if updated.parent_location_id is not None
                else None
            ),
            code=updated.code.value,
            name=updated.name.value,
            location_type=updated.location_type,
            is_active=updated.is_active,
        )
