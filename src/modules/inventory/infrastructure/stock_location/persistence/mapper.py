from typing import Any

from src.modules.inventory.domain.stock_location.aggregate import StockLocation


class StockLocationMapper:
    """Извлекает состояние самостоятельной локации без SQL и бизнес-проверок."""

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
