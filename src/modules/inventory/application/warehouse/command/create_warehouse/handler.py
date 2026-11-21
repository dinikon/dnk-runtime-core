from src.modules.inventory.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
)
from src.modules.inventory.application.warehouse.command.create_warehouse.dto import (
    CreateWarehouseResultDTO,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.repository import (
    StockLocationRepositoryProtocol,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateWarehouseHandler:
    """Создаёт склад и основную STORAGE через два порта одной транзакции."""

    def __init__(
        self,
        warehouses: WarehouseRepositoryProtocol,
        locations: StockLocationRepositoryProtocol,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты общего UoW и генератор идентификаторов."""
        self._warehouses = warehouses
        self._locations = locations
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: CreateWarehouseCommand
    ) -> CreateWarehouseResultDTO:
        """Подготавливает оба агрегата через Domain и сохраняет их без commit."""
        warehouse = Warehouse.create(
            identifier=WarehouseIdVO.from_value(self._uuid_generator.new()),
            code=WarehouseCodeVO(command.code),
            name=WarehouseNameVO(command.name),
        )
        location = StockLocation.create(
            identifier=StockLocationIdVO.from_value(self._uuid_generator.new()),
            warehouse=warehouse.snapshot(),
            code=LocationCodeVO("storage"),
            name=LocationNameVO("Основная зона хранения"),
            location_type=LocationType.STORAGE,
        )
        prepared = warehouse.set_default_storage_location(location.snapshot())
        await self._warehouses.add(warehouse)
        await self._locations.add(location)
        await self._warehouses.save(prepared)
        return CreateWarehouseResultDTO(
            id=prepared.id.uuid,
            code=prepared.code.value,
            name=prepared.name.value,
            is_active=prepared.is_active,
            default_storage_location_id=location.id.uuid,
        )
