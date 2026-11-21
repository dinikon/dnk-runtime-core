from src.modules.inventory.application.stock_lot.query.get_stock_lot.dto import (
    GetStockLotResultDTO,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.dto import (
    StockLotListItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)


class StockLotQueryMapper:
    """Преобразует ORM-модель в конкретные DTO чтения без восстановления Domain."""

    @staticmethod
    def to_details(model: StockLotModel) -> GetStockLotResultDTO:
        """Возвращает полную проекцию карточки с исходным номером и календарными датами."""
        return GetStockLotResultDTO(
            id=model.id,
            inventory_item_id=model.inventory_item_id,
            number=model.number,
            manufactured_on=model.manufactured_on,
            expires_on=model.expires_on,
        )

    @staticmethod
    def to_list_item(model: StockLotModel) -> StockLotListItemDTO:
        """Возвращает строку списка без ссылки на ORM-модель."""
        return StockLotListItemDTO(
            id=model.id,
            inventory_item_id=model.inventory_item_id,
            number=model.number,
            manufactured_on=model.manufactured_on,
            expires_on=model.expires_on,
        )
