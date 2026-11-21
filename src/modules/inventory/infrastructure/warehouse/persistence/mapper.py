from typing import Any

from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel,
)


class WarehouseMapper:
    """Преобразует состояние склада без SQL и бизнес-решений."""

    @staticmethod
    def to_domain(model: WarehouseModel) -> Warehouse:
        """Восстанавливает полный агрегат с сохранённой основной ссылкой."""
        return Warehouse.restore(
            identifier=WarehouseIdVO.from_value(model.id),
            code=WarehouseCodeVO(model.code),
            name=WarehouseNameVO(model.name),
            is_active=model.is_active,
            default_storage_location_id=(
                StockLocationIdVO.from_value(model.default_storage_location_id)
                if model.default_storage_location_id is not None
                else None
            ),
        )

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
