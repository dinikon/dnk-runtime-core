from collections.abc import Sequence

from sqlalchemy.engine import RowMapping

from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemBarcodeDTO,
    GetInventoryItemResultDTO,
)

from src.modules.inventory.application.inventory_item.query.list_inventory_items.dto import (
    InventoryItemListItemDTO,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class InventoryItemQueryMapper:
    """Преобразует SQL-проекции в строки списка без восстановления агрегатов."""

    @staticmethod
    def to_details(rows: Sequence[RowMapping]) -> GetInventoryItemResultDTO:
        """Собирает карточку из непустой проекции с внешним соединением штрихкодов."""
        row = rows[0]
        return GetInventoryItemResultDTO(
            id=row["id"],
            sku=row["sku"],
            base_uom=row["base_uom"],
            quantity_step=row["quantity_step"],
            tracking_mode=TrackingMode(row["tracking_mode"]),
            expiration_mode=ExpirationMode(row["expiration_mode"]),
            barcodes=tuple(
                GetInventoryItemBarcodeDTO(
                    id=child["barcode_id"], barcode=child["barcode"]
                )
                for child in rows
                if child["barcode_id"] is not None
            ),
        )

    @staticmethod
    def to_list_item(row: RowMapping) -> InventoryItemListItemDTO:
        """Собирает конкретный DTO из именованных полей SQL-результата."""
        return InventoryItemListItemDTO(
            id=row["id"],
            sku=row["sku"],
            base_uom=row["base_uom"],
            quantity_step=row["quantity_step"],
            tracking_mode=TrackingMode(row["tracking_mode"]),
            expiration_mode=ExpirationMode(row["expiration_mode"]),
        )
