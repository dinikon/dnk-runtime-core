from typing import Any

from src.modules.inventory.domain.warehouse.aggregate import Warehouse


class WarehouseMapper:
    """Извлекает состояние склада для DML без SQL и бизнес-решений."""

    @staticmethod
    def to_insert_values(warehouse: Warehouse) -> dict[str, Any]:
        """Сохраняет идентичность, настройки и необязательную основную ссылку."""
        return dict(
            id=warehouse.id.uuid,
            code=warehouse.code.value,
            name=warehouse.name.value,
            is_active=warehouse.is_active,
            default_storage_location_id=(
                warehouse.default_storage_location_id.uuid
                if warehouse.default_storage_location_id is not None
                else None
            ),
        )

    @staticmethod
    def to_update_values(warehouse: Warehouse) -> dict[str, Any]:
        """Извлекает состояние без изменения первичного ключа."""
        values = WarehouseMapper.to_insert_values(warehouse)
        del values["id"]
        return values
