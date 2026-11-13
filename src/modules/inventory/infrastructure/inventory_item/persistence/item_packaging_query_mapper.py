from src.modules.inventory.application.inventory_item.query.get_item_packaging.dto import (
    GetItemPackagingResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.dto import (
    ItemPackagingListItemDTO,
)
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)


class ItemPackagingQueryMapper:
    """Преобразует типизированную ORM-модель в конкретные DTO без восстановления Domain."""

    @staticmethod
    def to_details(model: ItemPackagingModel) -> GetItemPackagingResultDTO:
        """Собирает карточку упаковки с точным количеством содержимого."""
        return GetItemPackagingResultDTO(
            id=model.id,
            inventory_item_id=model.inventory_item_id,
            packaging_type_id=model.packaging_type_id,
            code=model.code,
            name=model.name,
            content_quantity=model.content_quantity,
            content_uom=model.content_uom,
        )

    @staticmethod
    def to_list_item(model: ItemPackagingModel) -> ItemPackagingListItemDTO:
        """Собирает отдельный контракт строки списка упаковок."""
        return ItemPackagingListItemDTO(
            id=model.id,
            inventory_item_id=model.inventory_item_id,
            packaging_type_id=model.packaging_type_id,
            code=model.code,
            name=model.name,
            content_quantity=model.content_quantity,
            content_uom=model.content_uom,
        )
