from collections.abc import Sequence

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
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)


class InventoryItemQueryMapper:
    """Преобразует ORM-модели в DTO чтения без восстановления доменных агрегатов."""

    @staticmethod
    def to_details(
        model: InventoryItemModel, barcodes: Sequence[ItemBarcodeModel]
    ) -> GetInventoryItemResultDTO:
        """Собирает карточку из позиции и штрихкодов в порядке SQL-проекции."""
        return GetInventoryItemResultDTO(
            id=model.id,
            sku=model.sku,
            base_uom=model.base_uom,
            quantity_step=model.quantity_step,
            tracking_mode=TrackingMode(model.tracking_mode),
            expiration_mode=ExpirationMode(model.expiration_mode),
            barcodes=tuple(
                GetInventoryItemBarcodeDTO(id=barcode.id, barcode=barcode.barcode)
                for barcode in barcodes
            ),
        )

    @staticmethod
    def to_list_item(model: InventoryItemModel) -> InventoryItemListItemDTO:
        """Собирает конкретный DTO списка из типизированной модели позиции."""
        return InventoryItemListItemDTO(
            id=model.id,
            sku=model.sku,
            base_uom=model.base_uom,
            quantity_step=model.quantity_step,
            tracking_mode=TrackingMode(model.tracking_mode),
            expiration_mode=ExpirationMode(model.expiration_mode),
        )
