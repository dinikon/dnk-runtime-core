from src.modules.inventory.application.stock_location.query.get_stock_location.dto import (
    GetStockLocationResultDTO,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    StockLocationListItemDTO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)


class StockLocationQueryMapper:
    """Собирает DTO чтения из типизированной модели без восстановления Domain."""

    @staticmethod
    def to_details(model: StockLocationModel) -> GetStockLocationResultDTO:
        """Явно преобразует собственные поля и nullable-ссылку родителя."""
        return GetStockLocationResultDTO(
            id=model.id,
            warehouse_id=model.warehouse_id,
            parent_location_id=model.parent_location_id,
            code=model.code,
            name=model.name,
            location_type=LocationType(model.location_type),
            is_active=model.is_active,
        )

    @staticmethod
    def to_list_item(model: StockLocationModel) -> StockLocationListItemDTO:
        """Явно преобразует собственные поля и nullable-ссылку родителя."""
        return StockLocationListItemDTO(
            id=model.id,
            warehouse_id=model.warehouse_id,
            parent_location_id=model.parent_location_id,
            code=model.code,
            name=model.name,
            location_type=LocationType(model.location_type),
            is_active=model.is_active,
        )
