from datetime import date
from uuid import UUID

from src.modules.inventory.domain.stock_lot.aggregate import StockLot


class StockLotMapper:
    """Подготавливает значения записи самостоятельной партии без I/O и бизнес-проверок."""

    @staticmethod
    def to_insert_values(lot: StockLot) -> dict[str, UUID | str | date | None]:
        """Сохраняет доменные ID, точный номер и date без времени."""
        return {
            "id": lot.id.uuid,
            "inventory_item_id": lot.inventory_item_id.uuid,
            "number": lot.number.value,
            "manufactured_on": lot.dates.manufactured_on,
            "expires_on": lot.dates.expires_on,
        }
