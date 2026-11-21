from typing import Any

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)


class StockLocationMapper:
    """Преобразует агрегат и модель самостоятельной локации без SQL."""

    @staticmethod
    def to_domain(model: StockLocationModel) -> StockLocation:
        """Восстанавливает агрегат с сохранёнными ID, принадлежностью и активностью."""
        return StockLocation.restore(
            identifier=StockLocationIdVO.from_value(model.id),
            warehouse_id=WarehouseIdVO.from_value(model.warehouse_id),
            parent_location_id=(
                StockLocationIdVO.from_value(model.parent_location_id)
                if model.parent_location_id is not None
                else None
            ),
            code=LocationCodeVO(model.code),
            name=LocationNameVO(model.name),
            location_type=LocationType(model.location_type),
            is_active=model.is_active,
        )

    @staticmethod
    def to_insert_values(location: StockLocation) -> dict[str, Any]:
        """Сохраняет ID и принадлежность адреса без новых идентификаторов."""
        return dict(
            id=location.id.uuid,
            warehouse_id=location.warehouse_id.uuid,
            parent_location_id=(
                location.parent_location_id.uuid
                if location.parent_location_id is not None
                else None
            ),
            code=location.code.value,
            name=location.name.value,
            location_type=location.location_type.value,
            is_active=location.is_active,
        )

    @staticmethod
    def to_update_values(location: StockLocation) -> dict[str, Any]:
        """Извлекает только изменяемые поля, сохраняя ID, склад, родителя и тип."""
        return dict(
            code=location.code.value,
            name=location.name.value,
            is_active=location.is_active,
        )
