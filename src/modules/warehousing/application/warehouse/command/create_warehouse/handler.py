from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.warehousing.application.port.time_zone_reader import (
    TimeZoneReaderProtocol,
)
from src.modules.warehousing.application.warehouse.command.create_warehouse.command import (
    CreateWarehouseCommand,
)
from src.modules.warehousing.application.warehouse.command.create_warehouse.dto import (
    CreateWarehouseResultDTO,
)
from src.modules.warehousing.domain.warehouse.aggregate import Warehouse
from src.modules.warehousing.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.domain.warehouse.value_object.policy import (
    WarehousePolicyVO,
)


class CreateWarehouseHandler:
    """Координирует создание склада и внешнюю проверку timezone без commit."""

    def __init__(
        self,
        *,
        repository: WarehouseRepositoryProtocol,
        time_zones: TimeZoneReaderProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает порты, собранные во внешнем UoW."""
        self._repository = repository
        self._time_zones = time_zones
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def execute(
        self, command: CreateWarehouseCommand
    ) -> CreateWarehouseResultDTO:
        """Проверяет настройки, добавляет агрегат и возвращает конкретный DTO."""
        policy = WarehousePolicyVO(command.timezone)
        timezone_is_active = await self._time_zones.is_active(policy.timezone)
        warehouse = Warehouse.create(
            warehouse_id=WarehouseIdVO.from_value(self._uuid_generator.new()),
            code=command.code,
            title=command.title,
            warehouse_type=command.warehouse_type,
            policy=policy,
            timezone_is_active=timezone_is_active,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(tenant_id=command.tenant_id, warehouse=warehouse)
        return CreateWarehouseResultDTO(
            id=warehouse.id.uuid,
            code=warehouse.code.value,
            status=warehouse.status.value,
            revision=warehouse.revision,
        )
