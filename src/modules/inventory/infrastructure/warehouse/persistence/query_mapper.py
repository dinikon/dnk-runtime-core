from src.modules.inventory.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseResultDTO,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.dto import (
    WarehouseListItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)


class WarehouseQueryMapper:
    """Преобразует типизированные модели в DTO без восстановления агрегата."""

    @staticmethod
    def to_details(model: WarehouseModel) -> GetWarehouseResultDTO:
        """Собирает проекцию отдельной карточки."""
        return GetWarehouseResultDTO(
            id=model.id,
            code=model.code,
            name=model.name,
            is_active=model.is_active,
            default_storage_location_id=model.default_storage_location_id,
        )

    @staticmethod
    def to_list_item(model: WarehouseModel) -> WarehouseListItemDTO:
        """Собирает строку списка без восстановления локаций."""
        return WarehouseListItemDTO(
            id=model.id,
            code=model.code,
            name=model.name,
            is_active=model.is_active,
            default_storage_location_id=model.default_storage_location_id,
        )
