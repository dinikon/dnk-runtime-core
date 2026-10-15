from src.modules.catalog.application.catalog_item.read_dto import CatalogItemReadDTO
from src.modules.catalog.application.catalog_item.query.list_catalog_items.row_dto import (
    CatalogItemListRowDTO,
)


class CatalogItemQueryMapper:
    """Формирует ограниченный контракт списка из согласованной read проекции."""

    @staticmethod
    def list_row(value: CatalogItemReadDTO) -> CatalogItemListRowDTO:
        """Не восстанавливает Aggregate и не включает editor own data в список."""
        gallery = value.effective.gallery
        image = (
            next((i for i in gallery.images if i.id == gallery.primary_image_id), None)
            if gallery
            else None
        )
        price = value.effective.price_specification
        return CatalogItemListRowDTO(
            value.own.id.uuid,
            value.own.kind,
            value.root_id,
            value.root_revision,
            value.own.revision,
            value.own.status,
            value.own.sku,
            (value.effective.content or {}).get("name"),
            value.effective.price,
            value.price_currency or (price.currency if price else None),
            value.price_min,
            value.price_max,
            value.price_incomplete,
            value.stock_status,
            image,
            value.effective.available_for_sale,
            value.effective.weight,
            value.effective.dimensions,
        )
