from src.modules.inventory.application.warehouse.command.update_warehouse.command import (
    UpdateWarehouseCommand,
)
from src.modules.inventory.application.warehouse.command.update_warehouse.dto import (
    UpdateWarehouseResultDTO,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError
from src.modules.inventory.domain.warehouse.repository import (
    WarehouseRepositoryProtocol,
)
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO


class UpdateWarehouseHandler:
    """Координирует изменение склада через Domain внутри внешнего UoW."""

    def __init__(self, repository: WarehouseRepositoryProtocol) -> None:
        """Принимает write-порт без доступа к сессии и управлению транзакцией."""
        self._repository = repository

    async def execute(
        self, command: UpdateWarehouseCommand
    ) -> UpdateWarehouseResultDTO:
        """Блокирует актуальный склад, применяет доменные методы и пропускает no-op."""
        fields = command.fields
        warehouse = await self._repository.get_for_update(command.warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError("Склад не найден.")
        updated = warehouse
        if "code" in fields and command.code is not None:
            updated = updated.change_code(WarehouseCodeVO(command.code))
        if "name" in fields and command.name is not None:
            updated = updated.rename(WarehouseNameVO(command.name))
        if "is_active" in fields:
            updated = updated.activate() if command.is_active else updated.deactivate()
        if updated != warehouse:
            await self._repository.save(updated)
        return UpdateWarehouseResultDTO(
            id=updated.id.uuid,
            code=updated.code.value,
            name=updated.name.value,
            is_active=updated.is_active,
            default_storage_location_id=(
                updated.default_storage_location_id.uuid
                if updated.default_storage_location_id is not None
                else None
            ),
        )
