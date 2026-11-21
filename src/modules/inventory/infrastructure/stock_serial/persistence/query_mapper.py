from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.dto import (
    GetStockSerialResultDTO,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.dto import (
    StockSerialListItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)


class StockSerialQueryMapper:
    """Преобразует ORM-модель в конкретные DTO чтения без восстановления Domain."""

    @staticmethod
    def to_details(
        model: StockSerialModel, lot: StockLotModel | None
    ) -> GetStockSerialResultDTO:
        """Возвращает полную проекцию карточки с исходным номером и календарными датами."""
        return GetStockSerialResultDTO(
            id=model.id,
            inventory_item_id=model.inventory_item_id,
            number=model.number,
            lot_id=model.lot_id,
            lot_number=lot.number if lot is not None else None,
            date_source="LOT" if model.lot_id is not None else "NONE",
            manufactured_on=lot.manufactured_on if lot is not None else None,
            expires_on=lot.expires_on if lot is not None else None,
        )

    @staticmethod
    def to_list_item(
        model: StockSerialModel, lot: StockLotModel | None
    ) -> StockSerialListItemDTO:
        """Возвращает строку списка без ссылки на ORM-модель."""
        return StockSerialListItemDTO(
            id=model.id,
            inventory_item_id=model.inventory_item_id,
            number=model.number,
            lot_id=model.lot_id,
            lot_number=lot.number if lot is not None else None,
            date_source="LOT" if model.lot_id is not None else "NONE",
            manufactured_on=lot.manufactured_on if lot is not None else None,
            expires_on=lot.expires_on if lot is not None else None,
        )
