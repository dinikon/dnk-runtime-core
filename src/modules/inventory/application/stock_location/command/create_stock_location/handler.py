from src.modules.inventory.application.stock_location.command.create_stock_location.command import (
    CreateStockLocationCommand,
)
from src.modules.inventory.application.stock_location.command.create_stock_location.dto import (
    CreateStockLocationResultDTO,
)
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateStockLocationHandler:
    """Координирует создание адреса по актуальному складу в транзакции внешнего UoW."""

    def __init__(
        self,
        warehouses: WarehouseRepositoryProtocol,
        locations: StockLocationRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты одной сессии и генератор ID без управления commit."""
        self._warehouses = warehouses
        self._locations = locations
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: CreateStockLocationCommand
    ) -> CreateStockLocationResultDTO:
        """Согласует чтение склада с деактивацией, вызывает фабрику и сохраняет адрес."""
        warehouse = await self._warehouses.get_for_share(command.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        parent = None
        if command.parent_location_id is not None:
            parent = await self._locations.get(command.parent_location_id)
            if parent is None:
                raise StockLocationNotFoundError("Родительская локация не найдена.")
        location = StockLocation.create(
            identifier=StockLocationIdVO.from_value(self._uuid_generator.new()),
            warehouse=warehouse.snapshot(),
            parent=parent.snapshot() if parent is not None else None,
            code=LocationCodeVO(command.code),
            name=LocationNameVO(command.name),
            location_type=command.location_type,
        )
        await self._locations.add(location)
        return CreateStockLocationResultDTO(
            id=location.id.uuid,
            warehouse_id=location.warehouse_id.uuid,
            parent_location_id=(
                location.parent_location_id.uuid
                if location.parent_location_id is not None
                else None
            ),
            code=location.code.value,
            name=location.name.value,
            location_type=location.location_type,
            is_active=location.is_active,
        )
